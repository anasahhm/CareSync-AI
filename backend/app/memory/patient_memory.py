"""
Patient Memory

Long-lived, cross-consultation memory for a single patient: prior chief
complaints, diagnoses, and risk trends. Reads from Postgres (the durable
source of truth) and writes a semantic index entry per completed
consultation so future consultations can retrieve "similar past visits."
"""
import logging
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.memory.semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)


class PatientMemory:
    def __init__(self, db: AsyncSession, semantic_memory: SemanticMemory):
        self.db = db
        self.semantic_memory = semantic_memory

    async def record_consultation_summary(
        self, patient_id: str, consultation_id: str, primary_diagnosis: Optional[str], risk_score: float
    ) -> None:
        summary_text = f"{primary_diagnosis or 'undetermined finding'} (risk={risk_score:.2f})"
        self.semantic_memory.add(
            scope_id=f"patient:{patient_id}",
            entry_id=consultation_id,
            text=summary_text,
            metadata={"consultation_id": consultation_id, "risk_score": risk_score},
        )

    def find_similar_past_visits(self, patient_id: str, current_complaint: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self.semantic_memory.search(scope_id=f"patient:{patient_id}", query=current_complaint, top_k=top_k)

    async def get_history(self, patient_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        from app.models import Consultation, AgentProcessingReport

        try:
            result = await self.db.execute(
                select(Consultation)
                .where(Consultation.patient_id == patient_id)
                .order_by(Consultation.created_at.desc())
                .limit(limit)
            )
            consultations = result.scalars().all()
            history = []
            for c in consultations:
                report_result = await self.db.execute(
                    select(AgentProcessingReport)
                    .where(AgentProcessingReport.consultation_id == c.id)
                    .order_by(AgentProcessingReport.started_at.desc())
                    .limit(1)
                )
                report = report_result.scalar_one_or_none()
                history.append({
                    "consultation_id": c.id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "chief_complaint": getattr(c, "chief_complaint", None),
                    "risk_score": report.overall_risk_score if report else None,
                })
            return history
        except Exception as e:
            logger.warning(f"PatientMemory: could not fetch history for {patient_id}: {e}")
            return []
