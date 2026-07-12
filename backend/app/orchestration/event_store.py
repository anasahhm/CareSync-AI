"""
Event Store

Two-tier store for agent events:
  - a bounded in-memory ring buffer per consultation, for fast realtime
    dashboard reads (used by the Socket.IO layer) without hitting the DB
    on every tick
  - a durable write-through to the AgentEventLog table for audit/history

This does not require Redis - it is a drop-in that can be swapped for a
Redis-backed store later (see `InMemoryRingBuffer`, the only class that would
need to change) without touching call sites, since both expose the same
`record` / `get_recent` interface.
"""
import logging
from collections import deque
from typing import Dict, List, Optional, Any, Deque

from sqlalchemy.ext.asyncio import AsyncSession

from app.communication import AgentEvent
from app.models import AgentEventLog, AgentEventType, AgentType

logger = logging.getLogger(__name__)


class InMemoryRingBuffer:
    """Per-consultation bounded event buffer, safe for single-process use."""

    def __init__(self, max_events_per_consultation: int = 500):
        self.max_events = max_events_per_consultation
        self._buffers: Dict[str, Deque[Dict[str, Any]]] = {}

    def record(self, consultation_id: str, event: Dict[str, Any]) -> None:
        buf = self._buffers.setdefault(consultation_id, deque(maxlen=self.max_events))
        buf.append(event)

    def get_recent(self, consultation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        buf = self._buffers.get(consultation_id)
        if not buf:
            return []
        return list(buf)[-limit:]

    def clear(self, consultation_id: str) -> None:
        self._buffers.pop(consultation_id, None)


class EventStore:
    """
    Facade used by the orchestrator / Socket.IO layer to record and query
    agent events. Wraps the in-memory ring buffer for hot reads and
    optionally persists to Postgres for durable history.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.ring_buffer = InMemoryRingBuffer()

    async def record_event(self, event: AgentEvent, processing_report_id: Optional[str] = None) -> None:
        self.ring_buffer.record(event.consultation_id, event.to_dict())

        if self.db is None or processing_report_id is None:
            return

        try:
            db_event_type = self._map_event_type(event.event_type.value)
            log_entry = AgentEventLog(
                processing_report_id=processing_report_id,
                agent_type=self._map_agent_type(event.source_agent),
                agent_id=event.source_agent_id,
                event_type=db_event_type,
                timestamp=event.timestamp,
                status=self._status_for_event(event.event_type.value),
                input_context=None,
            )
            self.db.add(log_entry)
            await self.db.flush()
        except Exception as e:
            # Never let audit persistence break live orchestration
            logger.warning(f"EventStore: failed to persist event, continuing with in-memory only: {e}")

    def get_recent_events(self, consultation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self.ring_buffer.get_recent(consultation_id, limit)

    def clear_consultation(self, consultation_id: str) -> None:
        self.ring_buffer.clear(consultation_id)

    @staticmethod
    def _map_event_type(runtime_event_type: str) -> AgentEventType:
        mapping = {
            "agent_started": AgentEventType.AGENT_STARTED,
            "agent_processing": AgentEventType.AGENT_PROCESSING,
            "agent_completed": AgentEventType.AGENT_COMPLETED,
            "agent_failed": AgentEventType.AGENT_FAILED,
            "recommendation_available": AgentEventType.RECOMMENDATION_GENERATED,
            "consensus_update": AgentEventType.CONSENSUS_REACHED,
            "escalation_required": AgentEventType.ESCALATION_TRIGGERED,
        }
        return mapping.get(runtime_event_type, AgentEventType.AGENT_PROCESSING)

    @staticmethod
    def _map_agent_type(source_agent: str) -> AgentType:
        try:
            return AgentType(source_agent)
        except ValueError:
            # Meta-sources like "ConsensusEngine" aren't real agents; log
            # them under the closest applicable type rather than crashing.
            return AgentType.CHIEF_ORCHESTRATOR if hasattr(AgentType, "CHIEF_ORCHESTRATOR") else AgentType.CLINICAL_REVIEW

    @staticmethod
    def _status_for_event(runtime_event_type: str) -> str:
        if runtime_event_type == "agent_completed":
            return "COMPLETED"
        if runtime_event_type == "agent_failed":
            return "FAILED"
        if runtime_event_type == "agent_started":
            return "PROCESSING"
        return "WAITING"
