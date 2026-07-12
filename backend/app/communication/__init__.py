"""
Agent Communication Layer

Provides abstract interface for agent communication.
Supports Band SDK (primary) with local event bus fallback.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Awaitable
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    AGENT_PROCESSING = "agent_processing"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    RECOMMENDATION_AVAILABLE = "recommendation_available"
    CONSENSUS_UPDATE = "consensus_update"
    ESCALATION_REQUIRED = "escalation_required"
    DEPENDENCY_MET = "dependency_met"
    # Added for extended agent roster (evidence/hallucination/QA/moderator/memory)
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    HALLUCINATION_FLAGGED = "hallucination_flagged"
    QUALITY_REVIEWED = "quality_reviewed"
    MODERATOR_DECISION = "moderator_decision"
    MEMORY_UPDATED = "memory_updated"
    VISION_OBSERVATION = "vision_observation"


@dataclass
class AgentEvent:
    event_id: str
    event_type: EventType
    source_agent: str
    source_agent_id: str
    timestamp: datetime
    consultation_id: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentEvent":
        data = data.copy()
        data["event_type"] = EventType(data["event_type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class AgentCommunicationBus(ABC):

    @abstractmethod
    async def publish(self, event: AgentEvent) -> bool:
        pass

    @abstractmethod
    async def subscribe(
        self,
        event_type: EventType,
        consultation_id: str,
        callback: Callable[[AgentEvent], Awaitable[None]]
    ) -> str:
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        pass

    @abstractmethod
    async def wait_for_event(
        self,
        event_type: EventType,
        consultation_id: str,
        timeout_seconds: int = 30,
        filter_fn: Optional[Callable[[AgentEvent], bool]] = None
    ) -> Optional[AgentEvent]:
        pass

    @abstractmethod
    async def get_event_history(
        self,
        consultation_id: str,
        limit: int = 100
    ) -> List[AgentEvent]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass


class AgentCommunicationLayer:

    def __init__(
        self,
        primary_bus: AgentCommunicationBus,
        fallback_bus: Optional[AgentCommunicationBus] = None
    ):
        self.primary_bus = primary_bus
        self.fallback_bus = fallback_bus
        self.current_bus = primary_bus
        self.fallback_active = False
        self._health_check_task = None
        self._global_listeners: List[Callable[["AgentEvent"], Awaitable[None]]] = []

    def add_global_listener(self, callback: Callable[["AgentEvent"], Awaitable[None]]) -> None:
        """Register a callback invoked on EVERY published event, regardless
        of consultation_id or event_type - used by the Socket.IO bridge so
        the frontend gets live updates without the bridge needing to know
        which consultations exist in advance."""
        self._global_listeners.append(callback)

    def remove_global_listener(self, callback: Callable[["AgentEvent"], Awaitable[None]]) -> None:
        if callback in self._global_listeners:
            self._global_listeners.remove(callback)

    async def start(self):
        if self.fallback_bus:
            self._health_check_task = asyncio.create_task(
                self._monitor_health()
            )

        logger.info("AgentCommunicationLayer started")

    async def stop(self):
        if self._health_check_task:
            self._health_check_task.cancel()

        logger.info("AgentCommunicationLayer stopped")

    async def _monitor_health(self):
        while True:
            try:
                await asyncio.sleep(10)

                healthy = await self.primary_bus.health_check()

                if not self.fallback_active and not healthy:
                    logger.warning(
                        "Primary communication bus unhealthy, switching to fallback"
                    )
                    self.current_bus = self.fallback_bus
                    self.fallback_active = True

                elif self.fallback_active and healthy:
                    logger.info(
                        "Primary communication bus restored, switching back"
                    )
                    self.current_bus = self.primary_bus
                    self.fallback_active = False

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def publish(self, event: AgentEvent) -> bool:
        try:
            result = await self.current_bus.publish(event)
            await self._notify_global_listeners(event)
            return result

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

            if not self.fallback_active and self.fallback_bus:
                self.current_bus = self.fallback_bus
                self.fallback_active = True

                try:
                    result = await self.fallback_bus.publish(event)
                    await self._notify_global_listeners(event)
                    return result

                except Exception as fallback_e:
                    logger.error(
                        f"Fallback publish failed: {fallback_e}"
                    )

            return False

    async def _notify_global_listeners(self, event: AgentEvent) -> None:
        for listener in self._global_listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.warning(f"Global event listener raised (non-fatal): {e}")

    async def subscribe(
        self,
        event_type: EventType,
        consultation_id: str,
        callback: Callable[[AgentEvent], Awaitable[None]]
    ) -> str:

        try:
            return await self.current_bus.subscribe(
                event_type,
                consultation_id,
                callback
            )

        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")

            if self.fallback_bus:
                return await self.fallback_bus.subscribe(
                    event_type,
                    consultation_id,
                    callback
                )

            raise

    async def unsubscribe(self, subscription_id: str) -> bool:
        try:
            return await self.current_bus.unsubscribe(subscription_id)

        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False

    async def wait_for_event(
        self,
        event_type: EventType,
        consultation_id: str,
        timeout_seconds: int = 30,
        filter_fn: Optional[Callable[[AgentEvent], bool]] = None
    ) -> Optional[AgentEvent]:

        try:
            return await self.current_bus.wait_for_event(
                event_type,
                consultation_id,
                timeout_seconds,
                filter_fn
            )

        except Exception as e:
            logger.error(f"Failed to wait for event: {e}")

            if self.fallback_bus:
                try:
                    return await self.fallback_bus.wait_for_event(
                        event_type,
                        consultation_id,
                        timeout_seconds,
                        filter_fn
                    )

                except Exception as fallback_e:
                    logger.error(
                        f"Fallback wait failed: {fallback_e}"
                    )

            return None

    async def get_event_history(
        self,
        consultation_id: str,
        limit: int = 100
    ) -> List[AgentEvent]:

        try:
            return await self.current_bus.get_event_history(
                consultation_id,
                limit
            )

        except Exception as e:
            logger.error(f"Failed to get event history: {e}")
            return []

    async def health_check(self) -> bool:
        try:
            return await self.current_bus.health_check()

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


def create_agent_event(
    event_type: EventType,
    source_agent: str,
    source_agent_id: str,
    consultation_id: str,
    payload: Dict[str, Any]
) -> AgentEvent:

    return AgentEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        source_agent=source_agent,
        source_agent_id=source_agent_id,
        timestamp=datetime.utcnow(),
        consultation_id=consultation_id,
        payload=payload
    )
from .local_event_bus import LocalEventBus

__all__ = [
    "AgentEvent",
    "EventType",
    "AgentCommunicationBus",
    "AgentCommunicationLayer",
    "create_agent_event",
    "LocalEventBus"
]