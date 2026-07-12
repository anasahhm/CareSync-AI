"""
Shared Memory

Cross-agent scratchpad for a single consultation run. Any agent can write a
named fact ("top_diagnosis", "care_pathway", ...) that any other agent
(regardless of execution order) can read, without going through the full
event-history replay that agents currently do in `_get_top_diagnosis`-style
helpers. Backed by RedisCache so it is safe across multiple backend worker
processes handling the same consultation concurrently (e.g. behind a load
balancer), same as ConsultationMemory.
"""
import logging
from typing import Any, Dict

from app.memory.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class SharedMemory:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    def _key(self, consultation_id: str) -> str:
        return f"shared_memory:{consultation_id}"

    async def write(self, consultation_id: str, fact_key: str, value: Any) -> None:
        state = await self.cache.get(self._key(consultation_id)) or {}
        state[fact_key] = value
        await self.cache.set(self._key(consultation_id), state, ttl_seconds=3600)

    async def read(self, consultation_id: str, fact_key: str, default: Any = None) -> Any:
        state = await self.cache.get(self._key(consultation_id)) or {}
        return state.get(fact_key, default)

    async def read_all(self, consultation_id: str) -> Dict[str, Any]:
        return await self.cache.get(self._key(consultation_id)) or {}

    async def clear(self, consultation_id: str) -> None:
        await self.cache.delete(self._key(consultation_id))
