"""
GestureMed AI — Pydantic Response Schemas
Centralised schemas used across routes for consistent API responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Consultation ──────────────────────────────────────────────────────────────

class ConsultationOut(BaseModel):
    id: str
    room_id: str
    status: str
    chief_complaint: Optional[str] = None
    doctor_notes: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Annotation ────────────────────────────────────────────────────────────────

class AnnotationOut(BaseModel):
    id: str
    annotation_type: str
    coordinates: dict
    body_region: Optional[str] = None
    note: Optional[str] = None
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Report ─────────────────────────────────────────────────────────────────

class AIReportOut(BaseModel):
    id: str
    consultation_id: str
    status: str
    summary: Optional[str] = None
    symptoms_observed: Optional[List[str]] = None
    areas_marked: Optional[List[str]] = None
    suggested_next_steps: Optional[List[str]] = None
    risk_indicators: Optional[List[str]] = None
    structured_data: Optional[dict] = None
    generated_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Doctor Public Profile ─────────────────────────────────────────────────────

class DoctorListingOut(BaseModel):
    id: str
    full_name: str
    specialization: str
    hospital: Optional[str] = None
    years_of_experience: int
    bio: Optional[str] = None
    consultation_fee: Optional[float] = None
    is_verified: bool
    available: bool


# ── Gesture Event ─────────────────────────────────────────────────────────────

class GestureEventOut(BaseModel):
    gesture_type: str
    confidence: float
    action_taken: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── Generic ───────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    status: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int
