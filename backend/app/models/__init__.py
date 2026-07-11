"""
GestureMed AI — SQLAlchemy ORM Models
Full database schema with all entities.
"""
import uuid
import enum
from datetime import datetime
from typing import Optional, List

from uuid6 import uuid7

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class ConsultationStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GestureType(str, enum.Enum):
    PINCH = "PINCH"
    PEACE = "PEACE"
    POINTING = "POINTING"
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"
    OPEN_PALM = "OPEN_PALM"
    FIST = "FIST"
    FINGERS_1 = "FINGERS_1"
    FINGERS_2 = "FINGERS_2"
    FINGERS_3 = "FINGERS_3"
    FINGERS_4 = "FINGERS_4"
    FINGERS_5 = "FINGERS_5"


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    doctor_profile: Mapped[Optional["DoctorProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    patient_profile: Mapped[Optional["PatientProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


# ── Profiles ──────────────────────────────────────────────────────────────────

class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    hospital: Mapped[Optional[str]] = mapped_column(String(255))
    license_number: Mapped[Optional[str]] = mapped_column(String(100))
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    consultation_fee: Mapped[Optional[float]] = mapped_column(Float)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="doctor_profile")
    consultations: Mapped[List["Consultation"]] = relationship(back_populates="doctor")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    blood_type: Mapped[Optional[str]] = mapped_column(String(10))
    medical_history: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    allergies: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    current_medications: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    emergency_contact: Mapped[Optional[dict]] = mapped_column(JSON)

    user: Mapped["User"] = relationship(back_populates="patient_profile")
    consultations: Mapped[List["Consultation"]] = relationship(back_populates="patient")


# ── Consultation ──────────────────────────────────────────────────────────────

class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"))
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctor_profiles.id", ondelete="SET NULL"), nullable=True)
    room_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[ConsultationStatus] = mapped_column(
        SAEnum(ConsultationStatus), default=ConsultationStatus.SCHEDULED
    )
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text)
    doctor_notes: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    recording_url: Mapped[Optional[str]] = mapped_column(String(500))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["PatientProfile"] = relationship(back_populates="consultations")
    doctor: Mapped[Optional["DoctorProfile"]] = relationship(back_populates="consultations")
    annotations: Mapped[List["Annotation"]] = relationship(
        back_populates="consultation", cascade="all, delete-orphan"
    )
    gesture_events: Mapped[List["GestureEvent"]] = relationship(
        back_populates="consultation", cascade="all, delete-orphan"
    )
    ai_report: Mapped[Optional["AIReport"]] = relationship(
        back_populates="consultation", uselist=False, cascade="all, delete-orphan"
    )
    agent_processing_report: Mapped[Optional["AgentProcessingReport"]] = relationship(
        back_populates="consultation", uselist=False, cascade="all, delete-orphan"
    )


# ── Annotations ───────────────────────────────────────────────────────────────

class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id", ondelete="CASCADE"))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    annotation_type: Mapped[str] = mapped_column(String(50))  # point, circle, region, text
    coordinates: Mapped[dict] = mapped_column(JSON, nullable=False)  # {x, y, radius, label, ...}
    body_region: Mapped[Optional[str]] = mapped_column(String(100))
    note: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[Optional[str]] = mapped_column(String(20), default="#FF6B6B")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    consultation: Mapped["Consultation"] = relationship(back_populates="annotations")


# ── Gesture Events ────────────────────────────────────────────────────────────

class GestureEvent(Base):
    __tablename__ = "gesture_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid7())
    )
    consultation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("consultations.id", ondelete="CASCADE")
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    gesture_type: Mapped[Optional[str]] = mapped_column(String)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)

    consultation: Mapped["Consultation"] = relationship(back_populates="gesture_events")


# ── AI Reports ────────────────────────────────────────────────────────────────

class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id: Mapped[str] = mapped_column(
        ForeignKey("consultations.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(ReportStatus), default=ReportStatus.PENDING
    )
    structured_data: Mapped[Optional[dict]] = mapped_column(JSON)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    symptoms_observed: Mapped[Optional[List[str]]] = mapped_column(JSON)
    areas_marked: Mapped[Optional[List[str]]] = mapped_column(JSON)
    suggested_next_steps: Mapped[Optional[List[str]]] = mapped_column(JSON)
    risk_indicators: Mapped[Optional[List[str]]] = mapped_column(JSON)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500))
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    consultation: Mapped["Consultation"] = relationship(back_populates="ai_report")


# ── Appointments ──────────────────────────────────────────────────────────────

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    doctor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Medical Files ─────────────────────────────────────────────────────────────

class MedicalFile(Base):
    __tablename__ = "medical_files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    consultation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("consultations.id", ondelete="SET NULL"))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))  # scan, report, prescription
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Audit Logs ────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")


# ── Band of Agents Models ─────────────────────────────────────────────────────

class AgentType(str, enum.Enum):
    CLINICAL_REVIEW = "CLINICAL_REVIEW"
    COMPLIANCE_PRIVACY = "COMPLIANCE_PRIVACY"
    MEDICAL_HISTORY = "MEDICAL_HISTORY"
    TREATMENT_RECOMMENDATION = "TREATMENT_RECOMMENDATION"
    INSURANCE_VERIFICATION = "INSURANCE_VERIFICATION"
    TRIAGE_ESCALATION = "TRIAGE_ESCALATION"
    FOLLOWUP_COORDINATION = "FOLLOWUP_COORDINATION"
    # Extended roster (added in V2, run alongside the original 7)
    CHIEF_ORCHESTRATOR = "CHIEF_ORCHESTRATOR"
    SYMPTOM = "SYMPTOM"
    DIAGNOSTIC = "DIAGNOSTIC"
    MEDICAL_RESEARCH = "MEDICAL_RESEARCH"
    EVIDENCE = "EVIDENCE"
    HALLUCINATION_DETECTION = "HALLUCINATION_DETECTION"
    QUALITY_ASSURANCE = "QUALITY_ASSURANCE"
    CONSENSUS_MODERATOR = "CONSENSUS_MODERATOR"
    EXPLANATION = "EXPLANATION"
    ESCALATION = "ESCALATION"


class AgentEventType(str, enum.Enum):
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_PROCESSING = "AGENT_PROCESSING"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    AGENT_WAITING = "AGENT_WAITING"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    CONSENSUS_REACHED = "CONSENSUS_REACHED"
    ESCALATION_TRIGGERED = "ESCALATION_TRIGGERED"


class EscalationLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentProcessingReport(Base):
    """
    Master report for agent orchestration results.
    One per consultation after agents complete processing.
    """
    __tablename__ = "agent_processing_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id: Mapped[str] = mapped_column(
        ForeignKey("consultations.id", ondelete="CASCADE"), unique=True, index=True
    )
    
    # Orchestration Metadata
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    
    # Agent Execution Summary
    agents_executed: Mapped[List[str]] = mapped_column(JSON, default=list)  # ["CLINICAL_REVIEW", ...]
    agents_failed: Mapped[List[str]] = mapped_column(JSON, default=list)
    agents_skipped: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Consensus & Risk
    consensus_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    overall_risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    escalation_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_level: Mapped[Optional[EscalationLevel]] = mapped_column(SAEnum(EscalationLevel))
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Final Outputs
    master_recommendations: Mapped[Optional[dict]] = mapped_column(JSON)
    critical_alerts: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    compliance_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    # Status & Auditability
    processing_status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    consultation: Mapped["Consultation"] = relationship(back_populates="agent_processing_report")
    agent_events: Mapped[List["AgentEventLog"]] = relationship(
        back_populates="processing_report", cascade="all, delete-orphan"
    )
    agent_recommendations: Mapped[List["AgentRecommendation"]] = relationship(
        back_populates="processing_report", cascade="all, delete-orphan"
    )
    escalation_events: Mapped[List["EscalationEvent"]] = relationship(
        back_populates="processing_report", cascade="all, delete-orphan"
    )
    consensus: Mapped[Optional["AgentConsensus"]] = relationship(
        back_populates="processing_report", uselist=False, cascade="all, delete-orphan"
    )


class AgentEventLog(Base):
    """
    Audit trail for each agent's execution.
    Tracks: start, processing, completion, failures, outputs.
    """
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    processing_report_id: Mapped[str] = mapped_column(
        ForeignKey("agent_processing_reports.id", ondelete="CASCADE"), index=True
    )
    
    # Agent Identity
    agent_type: Mapped[AgentType] = mapped_column(SAEnum(AgentType), index=True)
    agent_id: Mapped[str] = mapped_column(String(100), index=True)  # Unique per agent instance
    
    # Event Tracking
    event_type: Mapped[AgentEventType] = mapped_column(SAEnum(AgentEventType))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Processing Details
    status: Mapped[str] = mapped_column(String(50))  # WAITING, PROCESSING, COMPLETED, FAILED
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Data & Reasoning
    input_context: Mapped[Optional[dict]] = mapped_column(JSON)
    agent_output: Mapped[Optional[dict]] = mapped_column(JSON)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-1
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    
    # Error Tracking
    error: Mapped[Optional[str]] = mapped_column(Text)
    error_code: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Dependencies
    waited_for_agents: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)  # Agent IDs this agent waited for
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    processing_report: Mapped["AgentProcessingReport"] = relationship(back_populates="agent_events")


class AgentRecommendation(Base):
    """
    Individual recommendation from an agent.
    Each agent can generate multiple recommendations.
    """
    __tablename__ = "agent_recommendations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    processing_report_id: Mapped[str] = mapped_column(
        ForeignKey("agent_processing_reports.id", ondelete="CASCADE"), index=True
    )
    agent_event_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("agent_events.id", ondelete="SET NULL"), nullable=True
    )
    
    # Source
    source_agent: Mapped[AgentType] = mapped_column(SAEnum(AgentType), index=True)
    source_agent_id: Mapped[str] = mapped_column(String(100), index=True)
    
    # Recommendation
    recommendation_type: Mapped[str] = mapped_column(String(100))  # diagnosis, treatment, follow-up, insurance, etc.
    recommendation_text: Mapped[str] = mapped_column(Text)
    recommendation_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Structured data for the recommendation
    
    # Confidence & Priority
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8)  # 0-1
    priority: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Justification
    supporting_evidence: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    
    # Override Status
    overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text)
    overridden_by_agent: Mapped[Optional[str]] = mapped_column(String(100))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    processing_report: Mapped["AgentProcessingReport"] = relationship(back_populates="agent_recommendations")


class EscalationEvent(Base):
    """
    Tracks escalation triggers during agent processing.
    E.g., high-risk patient, compliance violation, critical condition.
    """
    __tablename__ = "escalation_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    processing_report_id: Mapped[str] = mapped_column(
        ForeignKey("agent_processing_reports.id", ondelete="CASCADE"), index=True
    )
    
    # Escalation Identity
    escalation_level: Mapped[EscalationLevel] = mapped_column(SAEnum(EscalationLevel), index=True)
    escalation_reason: Mapped[str] = mapped_column(String(255))
    escalation_type: Mapped[str] = mapped_column(String(100))  # medical_emergency, compliance_breach, insurance_issue, etc.
    
    # Source
    triggered_by_agent: Mapped[AgentType] = mapped_column(SAEnum(AgentType))
    triggered_by_agent_id: Mapped[str] = mapped_column(String(100))
    
    # Details
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    required_action: Mapped[Optional[str]] = mapped_column(Text)
    
    # Follow-up
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(100))  # User ID or agent ID
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    processing_report: Mapped["AgentProcessingReport"] = relationship(back_populates="escalation_events")


class AgentConsensus(Base):
    """
    Final consensus state after all agents complete.
    Synthesizes: agreement levels, override chains, final decisions.
    """
    __tablename__ = "agent_consensus"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    processing_report_id: Mapped[str] = mapped_column(
        ForeignKey("agent_processing_reports.id", ondelete="CASCADE"), unique=True, index=True
    )
    
    # Consensus Metrics
    total_agents_executed: Mapped[int] = mapped_column(Integer)
    total_agents_agreed: Mapped[int] = mapped_column(Integer)  # Agents voting same direction
    consensus_percentage: Mapped[float] = mapped_column(Float)  # 0-100
    
    # Primary Decisions
    primary_diagnosis: Mapped[Optional[str]] = mapped_column(String(500))
    diagnosis_confidence: Mapped[Optional[float]] = mapped_column(Float)
    
    primary_treatment_plan: Mapped[Optional[str]] = mapped_column(Text)
    treatment_confidence: Mapped[Optional[float]] = mapped_column(Float)
    
    # Risk Assessment
    risk_level: Mapped[EscalationLevel] = mapped_column(SAEnum(EscalationLevel), default=EscalationLevel.LOW)
    risk_factors: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    # Agreements & Disagreements
    agent_agreements: Mapped[Optional[dict]] = mapped_column(JSON)  # {agent_type: {agreement_type: count}}
    conflicting_recommendations: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    # Final Actions
    final_recommendations: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    requires_doctor_review: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    processing_report: Mapped["AgentProcessingReport"] = relationship(back_populates="consensus")