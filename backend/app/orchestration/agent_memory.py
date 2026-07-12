"""
Agent Memory

Short-term (per-consultation, in-process) and long-term (per-patient,
DB-backed) memory for agents. No Redis/Qdrant dependency required to run -
short-term memory lives in a process-local dict, long-term memory is read
from the existing Consultation / AgentProcessingReport tables so it works
with zero new infrastructure. The interface is intentionally the seam to
swap in Redis (short-term) and Qdrant (semantic long-term search) later:
replace `ShortTermMemory`'s dict with a Redis client and `LongTermMemory`'s
DB query with a vector search, without touching AgentMemoryStore call sites.
"""
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Working memory scoped to a single consultation's processing run."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def set(self, consultation_id: str, key: str, value: Any) -> None:
        self._store.setdefault(consultation_id, {})[key] = value

    def get(self, consultation_id: str, key: str, default: Any = None) -> Any:
        return self._store.get(consultation_id, {}).get(key, default)

    def get_all(self, consultation_id: str) -> Dict[str, Any]:
        return dict(self._store.get(consultation_id, {}))

    def clear(self, consultation_id: str) -> None:
        self._store.pop(consultation_id, None)


class LongTermMemory:
    """
    Patient-level memory drawn from prior consultations. Read-only summary
    view - does not mutate historical records.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_patient_history_summary(self, patient_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        from app.models import Consultation, AgentProcessingReport

        try:
            result = await self.db.execute(
                select(Consultation)
                .where(Consultation.patient_id == patient_id)
                .order_by(Consultation.created_at.desc())
                .limit(limit)
            )
            consultations = result.scalars().all()

            summaries = []
            for consultation in consultations:
                report_result = await self.db.execute(
                    select(AgentProcessingReport)
                    .where(AgentProcessingReport.consultation_id == consultation.id)
                    .order_by(AgentProcessingReport.started_at.desc())
                    .limit(1)
                )
                report = report_result.scalar_one_or_none()
                summaries.append({
                    "consultation_id": consultation.id,
                    "created_at": consultation.created_at.isoformat() if consultation.created_at else None,
                    "chief_complaint": getattr(consultation, "chief_complaint", None),
                    "primary_diagnosis": (report.master_recommendations[0]["text"]
                                           if report and report.master_recommendations else None),
                    "risk_score": report.overall_risk_score if report else None,
                })
            return summaries
        except Exception as e:
            logger.warning(f"LongTermMemory: could not fetch patient history for {patient_id}: {e}")
            return []


class AgentMemoryStore:
    """Facade combining short-term and long-term memory for agent use."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(db) if db is not None else None

    async def get_context_bundle(self, consultation_id: str, patient_id: str) -> Dict[str, Any]:
        bundle = {"short_term": self.short_term.get_all(consultation_id), "long_term": []}
        if self.long_term:
            bundle["long_term"] = await self.long_term.get_patient_history_summary(patient_id)
        return bundle

    def remember(self, consultation_id: str, key: str, value: Any) -> None:
        self.short_term.set(consultation_id, key, value)

    def recall(self, consultation_id: str, key: str, default: Any = None) -> Any:
        return self.short_term.get(consultation_id, key, default)

    def forget_consultation(self, consultation_id: str) -> None:
        self.short_term.clear(consultation_id)
