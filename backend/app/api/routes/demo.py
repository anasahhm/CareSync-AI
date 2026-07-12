"""
Demo Mode API

One-click agent demo with seeded consultation data.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Consultation, PatientProfile
from app.services.agent_service import get_agent_service

logger = logging.getLogger(__name__)
router = APIRouter()

DEMO_PATIENT_DATA = {
    "name": "John Doe",
    "medical_history": {
        "previous_injuries": ["Previous Shoulder Injury"],
        "chronic_conditions": [],
        "surgeries": []
    },
    "allergies": ["Aspirin"],
    "current_medications": [],
    "insurance_plan": "PPO",
    "insurance_active": True
}

DEMO_CONSULTATION = {
    "chief_complaint": "Shoulder Pain",
    "pain_score": 4,
    "doctor_notes": "Likely Rotator Cuff Strain",
    "duration_minutes": 15
}


@router.post("/demo/run")
async def run_agent_demo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run one-click demo with seeded consultation.
    
    Creates temporary patient and consultation, runs all 7 agents,
    streams events via Socket.IO, and returns complete report.
    """
    
    try:
        # Create demo patient
        demo_patient = PatientProfile(
            user_id=current_user.id,
            full_name=DEMO_PATIENT_DATA["name"],
            date_of_birth=datetime(1985, 6, 15).date(),
            medical_history=DEMO_PATIENT_DATA["medical_history"],
            allergies=DEMO_PATIENT_DATA["allergies"],
            current_medications=DEMO_PATIENT_DATA["current_medications"]
        )
        db.add(demo_patient)
        await db.flush()
        
        # Create demo consultation
        demo_consultation = Consultation(
            patient_id=demo_patient.id,
            doctor_id=current_user.id if current_user.role == "DOCTOR" else None,
            room_id=f"demo-{datetime.utcnow().timestamp()}",
            chief_complaint=DEMO_CONSULTATION["chief_complaint"],
            doctor_notes=DEMO_CONSULTATION["doctor_notes"],
            duration_minutes=DEMO_CONSULTATION["duration_minutes"],
            status="IN_PROGRESS",
            started_at=datetime.utcnow()
        )
        db.add(demo_consultation)
        await db.flush()
        
        logger.info(f"Created demo consultation {demo_consultation.id}")
        
        # Get agent service
        agent_service = await get_agent_service()
        
        # Build agent context from demo data
        from app.agents import AgentContext
        
        context = AgentContext(
            consultation_id=demo_consultation.id,
            patient_id=demo_patient.id,
            doctor_id=demo_consultation.doctor_id,
            chief_complaint=demo_consultation.chief_complaint,
            pain_score=DEMO_CONSULTATION["pain_score"],
            medical_history=demo_patient.medical_history,
            allergies=demo_patient.allergies,
            current_medications=demo_patient.current_medications,
            doctor_notes=demo_consultation.doctor_notes,
            annotations=[],
            gesture_events=[],
            consultation_duration_minutes=demo_consultation.duration_minutes
        )
        
        # Process through agents
        result = await agent_service.process_consultation(
            consultation_id=demo_consultation.id,
            context=context,
            db=db
        )
        
        if result["status"] == "FAILED":
            raise HTTPException(500, f"Demo failed: {result.get('error')}")
        
        # Mark consultation as completed
        demo_consultation.status = "COMPLETED"
        demo_consultation.ended_at = datetime.utcnow()
        db.add(demo_consultation)
        await db.commit()
        
        logger.info(f"Demo completed successfully: {demo_consultation.id}")
        
        return {
            "status": "COMPLETED",
            "consultation_id": demo_consultation.id,
            "processing_report": {
                "id": result["processing_report"].id,
                "status": result["processing_report"].processing_status,
                "duration_seconds": result["duration_seconds"],
                "consensus_score": result["consensus"].get("consensus_score", 0),
                "risk_score": result["consensus"].get("overall_risk_score", 0),
                "agents_executed": result["processing_report"].agents_executed or [],
                "recommendations": result["consensus"].get("final_recommendations", [])[:5]
            }
        }
    
    except Exception as e:
        logger.error(f"Demo execution failed: {e}", exc_info=True)
        raise HTTPException(500, f"Demo failed: {str(e)}")


@router.get("/demo/status/{consultation_id}")
async def get_demo_status(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of a demo consultation"""
    
    consultation_result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    
    if not consultation:
        raise HTTPException(404, "Consultation not found")
    
    return {
        "consultation_id": consultation_id,
        "status": consultation.status,
        "chief_complaint": consultation.chief_complaint,
        "started_at": consultation.started_at,
        "ended_at": consultation.ended_at
    }