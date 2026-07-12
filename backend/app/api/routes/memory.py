"""CareSyncAI V2 — Memory Visualization API"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.agent_service import get_agent_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/consultation/{consultation_id}")
async def get_consultation_memory(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Short-term memory for a single consultation: turns + per-agent outputs recorded so far."""
    agent_service = await get_agent_service()
    if not agent_service.memory_manager:
        raise HTTPException(status_code=503, detail="Memory system not initialized")

    state = await agent_service.memory_manager.consultation_memory.get_all(consultation_id)
    shared_facts = await agent_service.memory_manager.shared_memory.read_all(consultation_id)

    return {
        "consultation_id": consultation_id,
        "turns": state.get("turns", []),
        "agent_outputs": {
            agent_type: {
                "status": output.get("status"),
                "confidence": output.get("confidence"),
                "recommendation_count": len(output.get("recommendations", [])),
                "escalation_count": len(output.get("escalations", [])),
            }
            for agent_type, output in state.get("agent_outputs", {}).items()
        },
        "shared_facts": shared_facts,
    }


@router.get("/patient/{patient_id}")
async def get_patient_memory(
    patient_id: str,
    query: str = Query(default="", description="Optional query for semantic similarity search over past visits"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Long-term memory for a patient: consultation history plus optional semantic recall."""
    agent_service = await get_agent_service()
    if not agent_service.memory_manager:
        raise HTTPException(status_code=503, detail="Memory system not initialized")

    patient_memory = agent_service.memory_manager.patient_memory_for(db)
    history = await patient_memory.get_history(patient_id, limit=limit)

    similar_visits = []
    if query:
        similar_visits = patient_memory.find_similar_past_visits(patient_id, query, top_k=5)

    return {
        "patient_id": patient_id,
        "history": history,
        "similar_visits": similar_visits,
        "semantic_backend": "sentence_transformers" if agent_service.memory_manager.semantic_memory._model else "bag_of_words_fallback",
    }


@router.get("/health")
async def memory_health(current_user: User = Depends(get_current_user)):
    agent_service = await get_agent_service()
    if not agent_service.memory_manager:
        raise HTTPException(status_code=503, detail="Memory system not initialized")
    return await agent_service.memory_manager.health_check()
