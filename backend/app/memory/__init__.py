"""
Memory Layer

Exports the full memory stack: RedisCache (backing store, with automatic
in-process fallback), ConsultationMemory (short-term), PatientMemory
(long-term), SemanticMemory (embedding similarity search), SharedMemory
(cross-agent scratchpad), ConversationRecall (compression), and
MemoryManager (facade wiring all of the above together for the
orchestrator and agents to use).
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.redis_cache import RedisCache
from app.memory.semantic_memory import SemanticMemory
from app.memory.consultation_memory import ConsultationMemory
from app.memory.patient_memory import PatientMemory
from app.memory.shared_memory import SharedMemory
from app.memory.conversation_recall import ConversationRecall

logger = logging.getLogger(__name__)


class MemoryManager:
    """Single entry point the rest of the app uses to reach memory."""

    def __init__(self, redis_url: str):
        self.cache = RedisCache(redis_url)
        self.semantic_memory = SemanticMemory()
        self.consultation_memory = ConsultationMemory(self.cache)
        self.shared_memory = SharedMemory(self.cache)
        self._patient_memory: Optional[PatientMemory] = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        await self.cache.connect()
        self._initialized = True
        logger.info("MemoryManager initialized")

    def patient_memory_for(self, db: AsyncSession) -> PatientMemory:
        # PatientMemory needs a request-scoped DB session, so it's built
        # on demand rather than held on the manager singleton.
        return PatientMemory(db, self.semantic_memory)

    async def health_check(self) -> dict:
        return {
            "redis_connected": await self.cache.health_check(),
            "semantic_model_loaded": self.semantic_memory._model is not None,
        }

    async def shutdown(self):
        await self.cache.close()


__all__ = [
    "RedisCache",
    "SemanticMemory",
    "ConsultationMemory",
    "PatientMemory",
    "SharedMemory",
    "ConversationRecall",
    "MemoryManager",
]
