"""CareSyncAI V2 — RAG Visualization API"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models import User
from app.services.agent_service import get_agent_service

logger = logging.getLogger(__name__)
router = APIRouter()


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
async def rag_search(
    body: RagSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Runs a real hybrid (dense + BM25) retrieval for the given query and
    returns per-hit scores plus citations - used by the frontend RAG
    visualization to show retrieved documents, hybrid ranking, and evidence.
    """
    agent_service = await get_agent_service()
    if not agent_service.rag_manager:
        raise HTTPException(status_code=503, detail="RAG system not initialized")

    evidence_bundle = await agent_service.rag_manager.evidence_retriever.find_evidence(
        body.query, top_k=body.top_k
    )
    return evidence_bundle


@router.get("/health")
async def rag_health(current_user: User = Depends(get_current_user)):
    agent_service = await get_agent_service()
    if not agent_service.rag_manager:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    return await agent_service.rag_manager.health_check()
