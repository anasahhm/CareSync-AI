"""
Agent Processing API Routes

Endpoints for band of agents consultation processing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Consultation, AgentProcessingReport, PatientProfile, DoctorProfile, AgentConsensus
from app.services.agent_service import get_agent_service

router = APIRouter()


class ProcessWithAgentsRequest(BaseModel):
    """Request to process consultation with agent system"""
    pass


class AgentProcessingResponse(BaseModel):
    """Response from agent processing"""
    consultation_id: str
    processing_report_id: str
    status: str
    duration_seconds: float
    agent_count: int
    consensus_score: float
    escalations_count: int


@router.post("/process/{consultation_id}")
async def process_consultation_with_agents(
    consultation_id: str,
    body: ProcessWithAgentsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a consultation through the band of agents.
    
    Triggers: Clinical Review, Medical History, Compliance, Triage, Treatment, Insurance, Follow-up agents.
    Returns: Processing report with consensus and recommendations.
    """
    
    # Verify consultation exists
    consultation_result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(404, "Consultation not found")
    
    # Verify user has access (doctor or patient)
    if current_user.role == "PATIENT":
        patient_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or consultation.patient_id != patient.id:
            raise HTTPException(403, "Access denied")
    elif current_user.role == "DOCTOR":
        doctor_result = await db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or consultation.doctor_id != doctor.id:
            raise HTTPException(403, "Access denied")
    
    # Get patient and doctor data
    patient_result = await db.execute(
        select(PatientProfile).where(PatientProfile.id == consultation.patient_id)
    )
    patient_profile = patient_result.scalar_one_or_none()
    
    # Get agent service
    agent_service = await get_agent_service()
    
    # Process through agents
    result = await agent_service.process_consultation(
        consultation_id=consultation_id,
        patient_id=consultation.patient_id,
        doctor_id=consultation.doctor_id,
        chief_complaint=consultation.chief_complaint,
        doctor_notes=consultation.doctor_notes,
        medical_history=patient_profile.medical_history if patient_profile else {},
        annotations=[],  # Would load from database
        gesture_events=[],  # Would load from database
        patient_allergies=patient_profile.allergies if patient_profile else [],
        patient_medications=patient_profile.current_medications if patient_profile else [],
        patient_age=None,  # Would calculate from DOB
        insurance_plan=None,  # Would load from patient data
        db=db
    )
    
    if result["status"] == "FAILED":
        raise HTTPException(500, f"Agent processing failed: {result.get('error')}")
    
    processing_report = result["processing_report"]
    
    return AgentProcessingResponse(
        consultation_id=consultation_id,
        processing_report_id=processing_report.id,
        status=processing_report.processing_status,
        duration_seconds=processing_report.total_duration_seconds or 0,
        agent_count=len(processing_report.agents_executed),
        consensus_score=processing_report.consensus_score,
        escalations_count=len(processing_report.escalation_events) if processing_report.escalation_events else 0
    )


@router.get("/report/{consultation_id}")
async def get_agent_report(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get agent processing report for a consultation.
    
    Returns: Full processing report with agent events, recommendations, and consensus.
    """
    
    # Verify consultation exists
    consultation_result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(404, "Consultation not found")
    
    # Get processing report
    report_result = await db.execute(
        select(AgentProcessingReport).where(AgentProcessingReport.consultation_id == consultation_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "No agent processing report found for this consultation")
    
    return {
        "id": report.id,
        "consultation_id": report.consultation_id,
        "status": report.processing_status,
        "started_at": report.started_at,
        "completed_at": report.completed_at,
        "duration_seconds": report.total_duration_seconds,
        "agents_executed": report.agents_executed,
        "consensus_score": report.consensus_score,
        "risk_score": report.overall_risk_score,
        "escalation_triggered": report.escalation_triggered,
        "escalation_level": report.escalation_level,
        "recommendations": report.master_recommendations,
        "critical_alerts": report.critical_alerts,
        "compliance_flags": report.compliance_flags
    }


@router.get("/events/{consultation_id}")
async def get_agent_events(
    consultation_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get agent event timeline for a consultation.
    
    Returns: Chronological list of agent events for audit and transparency.
    """
    
    # Verify consultation exists
    consultation_result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(404, "Consultation not found")
    
    # Get processing report
    report_result = await db.execute(
        select(AgentProcessingReport).where(AgentProcessingReport.consultation_id == consultation_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        return {"events": []}
    
    # In full implementation, load agent_events from database
    return {
        "consultation_id": consultation_id,
        "report_id": report.id,
        "events": []  # Would load from AgentEvent table
    }


@router.get("/status/{consultation_id}")
async def get_agent_status(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current processing status for a consultation.
    
    Returns: Real-time status of agent execution.
    """
    
    # Verify consultation exists
    consultation_result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(404, "Consultation not found")
    
    # Get processing report
    report_result = await db.execute(
        select(AgentProcessingReport).where(AgentProcessingReport.consultation_id == consultation_id)
    )
    report = report_result.scalar_one_or_none()
    
    if not report:
        return {
            "consultation_id": consultation_id,
            "status": "NOT_STARTED",
            "progress": 0
        }
    
    return {
        "consultation_id": consultation_id,
        "status": report.processing_status,
        "agents_completed": len(report.agents_executed),
        "agents_total": 7,
        "progress": (len(report.agents_executed) / 7) * 100 if report.agents_executed else 0,
        "consensus_score": report.consensus_score,
        "risk_score": report.overall_risk_score,
        "escalations": len(report.escalation_events) if report.escalation_events else 0
    }


@router.get("/consensus/{consultation_id}")
async def get_consensus(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get agent consensus for a consultation.

    Returns: Final consensus from all agents including diagnosis, treatment, and agreements.
    """

    # Verify consultation exists
    consultation_result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(404, "Consultation not found")

    # Get processing report
    report_result = await db.execute(
        select(AgentProcessingReport).where(AgentProcessingReport.consultation_id == consultation_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "No consensus available yet")

    consensus_result = await db.execute(
        select(AgentConsensus).where(AgentConsensus.processing_report_id == report.id)
    )
    consensus = consensus_result.scalar_one_or_none()

    if not consensus:
        # Processing started but the consensus stage hasn't completed/persisted yet
        return {
            "consultation_id": consultation_id,
            "primary_diagnosis": None,
            "primary_treatment": None,
            "consensus_score": report.consensus_score,
            "risk_level": report.escalation_level,
            "agents_agreed": 0,
            "agents_total": 0,
            "final_recommendations": report.master_recommendations or [],
            "status": "pending",
        }

    return {
        "consultation_id": consultation_id,
        "primary_diagnosis": consensus.primary_diagnosis,
        "primary_treatment": None,
        "consensus_score": consensus.consensus_percentage / 100.0,
        "risk_level": consensus.risk_level.value if hasattr(consensus.risk_level, "value") else consensus.risk_level,
        "risk_factors": consensus.risk_factors or [],
        "agents_agreed": consensus.total_agents_agreed,
        "agents_total": consensus.total_agents_executed,
        "conflicting_recommendations": consensus.conflicting_recommendations or [],
        "final_recommendations": consensus.final_recommendations or report.master_recommendations or [],
        "requires_doctor_review": consensus.requires_doctor_review,
        "status": "complete",
    }


@router.get("/timeline/{consultation_id}")
async def get_agent_timeline(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Live/replayable agent execution timeline for the Consensus Timeline UI:
    every agent_started/agent_processing/agent_completed/agent_failed,
    recommendation, escalation, moderator decision, and consensus_update
    event published during this consultation's run, in order.
    """
    agent_service = await get_agent_service()
    if not agent_service.communication_layer:
        raise HTTPException(status_code=503, detail="Agent communication layer not initialized")

    history = await agent_service.communication_layer.get_event_history(consultation_id, limit=500)

    events = [
        {
            "event_type": event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
            "source_agent": event.source_agent,
            "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else event.timestamp,
            "payload": event.payload,
        }
        for event in history
    ]

    return {"consultation_id": consultation_id, "event_count": len(events), "events": events}