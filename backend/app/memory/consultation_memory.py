"""
Consultation Memory

Working memory scoped to a single in-progress consultation: rolling
conversation turns, agent outputs seen so far, and any doctor/patient
free-text notes exchanged during the live session. Backed by RedisCache so
it survives a backend process restart mid-consultation (shared memory
across FastAPI worker processes), with an in-process dict fallback.
"""
import logging
from typing import Dict, List, Any, Optional

from app.memory.redis_cache import RedisCache

logger = logging.getLogger(__name__)

MAX_TURNS_RETAINED = 200
MAX_AGENT_OUTPUTS_RETAINED = 30


class ConsultationMemory:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    def _key(self, consultation_id: str) -> str:
        return f"consultation_memory:{consultation_id}"

    async def append_turn(self, consultation_id: str, speaker: str, text: str) -> None:
        state = await self._get_state(consultation_id)
        state["turns"].append({"speaker": speaker, "text": text})
        state["turns"] = self._prune_turns(state["turns"])
        await self.cache.set(self._key(consultation_id), state, ttl_seconds=6 * 3600)

    async def record_agent_output(self, consultation_id: str, agent_type: str, output: Dict[str, Any]) -> None:
        state = await self._get_state(consultation_id)
        state["agent_outputs"][agent_type] = output
        if len(state["agent_outputs"]) > MAX_AGENT_OUTPUTS_RETAINED:
            # Evict oldest-inserted entries first (dict preserves insertion order)
            overflow = len(state["agent_outputs"]) - MAX_AGENT_OUTPUTS_RETAINED
            for key in list(state["agent_outputs"].keys())[:overflow]:
                del state["agent_outputs"][key]
        await self.cache.set(self._key(consultation_id), state, ttl_seconds=6 * 3600)

    async def get_turns(self, consultation_id: str) -> List[Dict[str, str]]:
        state = await self._get_state(consultation_id)
        return state["turns"]

    async def get_agent_output(self, consultation_id: str, agent_type: str) -> Optional[Dict[str, Any]]:
        state = await self._get_state(consultation_id)
        return state["agent_outputs"].get(agent_type)

    async def get_all(self, consultation_id: str) -> Dict[str, Any]:
        return await self._get_state(consultation_id)

    async def clear(self, consultation_id: str) -> None:
        await self.cache.delete(self._key(consultation_id))

    async def _get_state(self, consultation_id: str) -> Dict[str, Any]:
        state = await self.cache.get(self._key(consultation_id))
        if state is None:
            state = {"turns": [], "agent_outputs": {}}
        state.setdefault("turns", [])
        state.setdefault("agent_outputs", {})
        return state

    @staticmethod
    def _prune_turns(turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(turns) <= MAX_TURNS_RETAINED:
            return turns
        # Keep the earliest 10 (intake context) and the most recent bulk of
        # the cap, rather than a pure sliding window, so early intake
        # context isn't silently lost in a very long consultation.
        head = turns[:10]
        tail = turns[-(MAX_TURNS_RETAINED - 10):]
        return head + tail
