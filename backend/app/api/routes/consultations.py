"""
GestureMed AI — Consultations API
Full CRUD for consultation sessions with room management and status control.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    User, UserRole, Consultation, ConsultationStatus,
    DoctorProfile, PatientProfile
)

router = APIRouter()


class CreateConsultationRequest(BaseModel):
    chief_complaint: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class UpdateConsultationRequest(BaseModel):
    doctor_notes: Optional[str] = None
    status: Optional[ConsultationStatus] = None


@router.post("/", status_code=201)
async def create_consultation(
    body: CreateConsultationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patient creates a new consultation session."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(403, "Only patients can initiate consultations")

    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient profile not found. Complete onboarding first.")

    room_id = f"room_{uuid.uuid4().hex[:12]}"
    consultation = Consultation(
        patient_id=patient.id,
        room_id=room_id,
        chief_complaint=body.chief_complaint,
        scheduled_at=body.scheduled_at,
        status=ConsultationStatus.WAITING,
    )
    db.add(consultation)
    await db.commit()
    await db.refresh(consultation)

    return {
        "id": consultation.id,
        "room_id": consultation.room_id,
        "status": consultation.status,
        "chief_complaint": consultation.chief_complaint,
        "created_at": consultation.created_at,
    }


@router.get("/my")
async def my_consultations(
    status: Optional[ConsultationStatus] = Query(None),
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's consultations with optional status filter."""
    if current_user.role == UserRole.PATIENT:
        profile_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return []
        query = select(Consultation).where(Consultation.patient_id == profile.id)
    elif current_user.role == UserRole.DOCTOR:
        profile_result = await db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return []
        query = select(Consultation).where(Consultation.doctor_id == profile.id)
    else:
        query = select(Consultation)

    if status:
        query = query.where(Consultation.status == status)

    query = query.order_by(desc(Consultation.created_at)).limit(limit)
    result = await db.execute(query)
    consultations = result.scalars().all()

    return [
        {
            "id": c.id,
            "room_id": c.room_id,
            "status": c.status,
            "chief_complaint": c.chief_complaint,
            "doctor_notes": c.doctor_notes if current_user.role == UserRole.DOCTOR else None,
            "started_at": c.started_at,
            "ended_at": c.ended_at,
            "duration_seconds": c.duration_seconds,
            "created_at": c.created_at,
        }
        for c in consultations
    ]


@router.get("/waiting")
async def get_waiting_consultations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Doctors: see all consultations waiting for assignment."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(403, "Doctors only")

    result = await db.execute(
        select(Consultation)
        .where(Consultation.status == ConsultationStatus.WAITING)
        .where(Consultation.doctor_id.is_(None))
        .order_by(Consultation.created_at)
    )
    waiting = result.scalars().all()
    return [
        {
            "id": c.id,
            "room_id": c.room_id,
            "chief_complaint": c.chief_complaint,
            "created_at": c.created_at,
        }
        for c in waiting
    ]


@router.get("/{consultation_id}")
async def get_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")
    return {
        "id": c.id,
        "room_id": c.room_id,
        "status": c.status,
        "chief_complaint": c.chief_complaint,
        "doctor_notes": c.doctor_notes,
        "started_at": c.started_at,
        "ended_at": c.ended_at,
        "duration_seconds": c.duration_seconds,
        "created_at": c.created_at,
    }


@router.patch("/{consultation_id}")
async def update_consultation(
    consultation_id: str,
    body: UpdateConsultationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")

    if body.doctor_notes is not None:
        c.doctor_notes = body.doctor_notes

    if body.status is not None:
        c.status = body.status
        if body.status == ConsultationStatus.ACTIVE and not c.started_at:
            c.started_at = datetime.utcnow()
        elif body.status == ConsultationStatus.COMPLETED and not c.ended_at:
            c.ended_at = datetime.utcnow()
            if c.started_at:
                delta = c.ended_at - c.started_at
                c.duration_seconds = int(delta.total_seconds())

    await db.commit()
    return {"status": "updated", "id": c.id}


@router.post("/{consultation_id}/join")
async def join_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Doctor joins a waiting consultation — assigns themselves and activates it."""
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")

    if c.status == ConsultationStatus.COMPLETED:
        raise HTTPException(400, "Consultation already completed")

    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(404, "Doctor profile not found")

        if not c.doctor_id:
            c.doctor_id = doctor.id
            c.status = ConsultationStatus.ACTIVE
            c.started_at = c.started_at or datetime.utcnow()
            await db.commit()

    return {
        "room_id": c.room_id,
        "consultation_id": c.id,
        "status": c.status,
    }


@router.delete("/{consultation_id}")
async def cancel_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")

    if c.status == ConsultationStatus.ACTIVE:
        raise HTTPException(400, "Cannot cancel an active consultation. End it first.")

    c.status = ConsultationStatus.CANCELLED
    await db.commit()
    return {"status": "cancelled"}
