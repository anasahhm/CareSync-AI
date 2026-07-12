"""
GestureMed AI — Auth Routes
JWT login, registration (patient + doctor), token refresh, logout.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, hash_token
)
from app.core.config import settings
from app.models import User, UserRole, RefreshToken, DoctorProfile, PatientProfile

router = APIRouter()


# ── Request/Response Schemas ───────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class DoctorOnboardRequest(BaseModel):
    specialization: str
    hospital: str | None = None
    license_number: str | None = None
    years_of_experience: int = 0
    bio: str | None = None


class PatientOnboardRequest(BaseModel):
    date_of_birth: str | None = None
    gender: str | None = None
    blood_type: str | None = None
    allergies: list[str] = []
    current_medications: list[str] = []
    medical_history: dict = {}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.flush()  # get the ID

    # Create empty profile
    if body.role == UserRole.DOCTOR:
        db.add(DoctorProfile(user_id=user.id, specialization="General"))
    elif body.role == UserRole.PATIENT:
        db.add(PatientProfile(user_id=user.id))

    await db.commit()
    await db.refresh(user)

    access = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id)

    # Store refresh token
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires))
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user={"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name},
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id)

    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires))
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user={"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name},
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

    # Rotate refresh token
    stored.revoked = True

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(user.id, user.role.value)
    new_refresh = create_refresh_token(user.id)

    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(new_refresh), expires_at=expires))
    await db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user={"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name},
    )


@router.post("/logout")
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if stored:
        stored.revoked = True
        await db.commit()
    return {"detail": "Logged out successfully"}
