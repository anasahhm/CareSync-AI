"""
GestureMed AI — Users API
Profile management for patients, doctors, and admins.
"""
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models import User, UserRole, DoctorProfile, PatientProfile

router = APIRouter()


class UpdateDoctorProfileRequest(BaseModel):
    specialization: Optional[str] = None
    hospital: Optional[str] = None
    license_number: Optional[str] = None
    years_of_experience: Optional[int] = None
    bio: Optional[str] = None
    consultation_fee: Optional[float] = None
    available: Optional[bool] = None


class UpdatePatientProfileRequest(BaseModel):
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    current_medications: Optional[List[str]] = None
    medical_history: Optional[dict] = None
    emergency_contact: Optional[dict] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = None
    if current_user.role == UserRole.DOCTOR:
        result = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == current_user.id))
        doctor = result.scalar_one_or_none()
        if doctor:
            profile = {
                "specialization": doctor.specialization, "hospital": doctor.hospital,
                "license_number": doctor.license_number, "years_of_experience": doctor.years_of_experience,
                "bio": doctor.bio, "consultation_fee": doctor.consultation_fee,
                "is_verified": doctor.is_verified, "available": doctor.available,
            }
    elif current_user.role == UserRole.PATIENT:
        result = await db.execute(select(PatientProfile).where(PatientProfile.user_id == current_user.id))
        patient = result.scalar_one_or_none()
        if patient:
            profile = {
                "date_of_birth": patient.date_of_birth, "gender": patient.gender,
                "blood_type": patient.blood_type, "allergies": patient.allergies or [],
                "current_medications": patient.current_medications or [],
                "medical_history": patient.medical_history or {}, "emergency_contact": patient.emergency_contact,
            }
    return {
        "id": current_user.id, "email": current_user.email, "full_name": current_user.full_name,
        "role": current_user.role, "is_active": current_user.is_active, "is_verified": current_user.is_verified,
        "avatar_url": current_user.avatar_url, "created_at": current_user.created_at, "profile": profile,
    }


@router.patch("/me")
async def update_me(body: UpdateUserRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    await db.commit()
    return {"status": "updated"}


@router.patch("/me/doctor-profile")
async def update_doctor_profile(body: UpdateDoctorProfileRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(403, "Doctor only")
    result = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = DoctorProfile(user_id=current_user.id, specialization="General")
        db.add(profile)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    return {"status": "updated"}


@router.patch("/me/patient-profile")
async def update_patient_profile(body: UpdatePatientProfileRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(403, "Patient only")
    result = await db.execute(select(PatientProfile).where(PatientProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = PatientProfile(user_id=current_user.id)
        db.add(profile)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    return {"status": "updated"}


@router.get("/doctors")
async def list_doctors(available_only: bool = True, specialization: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = (
        select(User, DoctorProfile)
        .join(DoctorProfile, DoctorProfile.user_id == User.id)
        .where(User.role == UserRole.DOCTOR, User.is_active == True)
    )
    if available_only:
        query = query.where(DoctorProfile.available == True)
    if specialization:
        query = query.where(DoctorProfile.specialization.ilike(f"%{specialization}%"))
    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": user.id, "full_name": user.full_name, "specialization": profile.specialization,
            "hospital": profile.hospital, "years_of_experience": profile.years_of_experience,
            "bio": profile.bio, "consultation_fee": profile.consultation_fee,
            "is_verified": profile.is_verified, "available": profile.available,
        }
        for user, profile in rows
    ]


@router.get("/admin/all")
async def list_all_users(current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active, "created_at": u.created_at} for u in users]


@router.patch("/admin/{user_id}/verify")
async def verify_doctor(user_id: str, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_verified = True
    if user.role == UserRole.DOCTOR:
        doc = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == user_id))
        profile = doc.scalar_one_or_none()
        if profile:
            profile.is_verified = True
    await db.commit()
    return {"status": "verified"}


@router.patch("/admin/{user_id}/deactivate")
async def deactivate_user(user_id: str, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    await db.commit()
    return {"status": "deactivated"}
