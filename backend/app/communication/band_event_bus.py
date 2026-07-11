"""
Band Event Bus

Integration with Band SDK for agent communication.
Primary communication method with LocalEventBus fallback.

For this hackathon, we simulate Band using Redis pub/sub.
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Callable, List

from app.communication import (
    AgentEvent, EventType, AgentCommunicationBus
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class BandEventBus(AgentCommunicationBus):
    """
    Event bus using Band SDK integration.
    Falls back to local bus if Band is unavailable.
    
    For this implementation, we use Redis pub/sub as a Band simulator.
    In production, this would use actual Band SDK.
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.subscriptions: Dict[str, tuple] = {}  # subscription_id -> (event_type, consultation_id, callback)
        self.listening_tasks: Dict[str, asyncio.Task] = {}  # subscription_id -> Task
        self.healthy = True
        self._band_available = settings.BAND_ENABLED
    
    async def initialize(self, redis_client):
        """Initialize with Redis client"""
        self.redis = redis_client
        await self.health_check()
    
    async def publish(self, event: AgentEvent) -> bool:
        """Publish event via Band/Redis"""
        if not self._band_available:
            return False
        
        try:
            if not self.redis:
                return False
            
            # Create channel name from event type and consultation
            channel = f"agent:{event.consultation_id}:{event.event_type.value}"
            
            # Publish event
            event_data = json.dumps(event.to_dict())
            await self.redis.publish(channel, event_data)
            
            logger.debug(f"Band published event: {event.event_type} to {channel}")
            return True
        
        except Exception as e:
            logger.error(f"Band publish failed: {e}")
            self.healthy = False
            return False
    
    async def subscribe(
        self,
        event_type: EventType,
        consultation_id: str,
        callback: Optional[Callable] = None
    ) -> str:
        """Subscribe to events via Band/Redis"""
        if not self._band_available or not self.redis:
            raise RuntimeError("Band is not available")
        
        try:
            subscription_id = f"sub-{id(asyncio.current_task())}-{len(self.subscriptions)}"
            
            # Store subscription
            self.subscriptions[subscription_id] = (event_type, consultation_id, callback)
            
            # Create listening task
            channel = f"agent:{consultation_id}:{event_type.value}"
            task = asyncio.create_task(
                self._listen_channel(subscription_id, channel, callback)
            )
            self.listening_tasks[subscription_id] = task
            
            logger.debug(f"Band subscribed to {channel}")
            return subscription_id
        
        except Exception as e:
            logger.error(f"Band subscribe failed: {e}")
            raise
    
    async def _listen_channel(self, subscription_id: str, channel: str, callback: Optional[Callable]):
        """Listen to Redis channel and call callback"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event = AgentEvent.from_dict(event_data)
                        
                        if callback:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(event)
                            else:
                                callback(event)
                    
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
        
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        try:
            if subscription_id in self.subscriptions:
                del self.subscriptions[subscription_id]
            
            if subscription_id in self.listening_tasks:
                task = self.listening_tasks[subscription_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.listening_tasks[subscription_id]
            
            logger.debug(f"Band unsubscribed: {subscription_id}")
            return True
        
        except Exception as e:
            logger.error(f"Band unsubscribe failed: {e}")
            return False
    
    async def wait_for_event(
        self,
        event_type: EventType,
        consultation_id: str,
        timeout_seconds: int = 30,
        filter_fn: Optional[Callable] = None
    ) -> Optional[AgentEvent]:
        """Wait for event via Band/Redis"""
        if not self._band_available or not self.redis:
            return None
        
        received_event = None
        
        async def capture_callback(event):
            nonlocal received_event
            if filter_fn is None or filter_fn(event):
                received_event = event
        
        subscription_id = await self.subscribe(event_type, consultation_id, capture_callback)
        
        try:
            # Wait for event or timeout
            start = asyncio.get_event_loop().time()
            while True:
                if received_event:
                    return received_event
                
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed >= timeout_seconds:
                    return None
                
                await asyncio.sleep(0.1)
        
        finally:
            await self.unsubscribe(subscription_id)
    
    async def get_event_history(
        self,
        consultation_id: str,
        limit: int = 100
    ) -> List[AgentEvent]:
        """
        Get event history from Band.
        In Redis implementation, we would need to store events in a sorted set.
        For now, return empty list (would be implemented in full Band integration).
        """
        # Note: Full implementation would use Redis sorted set with timestamps
        logger.warning("Event history not yet implemented for Band")
        return []
    
    async def health_check(self) -> bool:
        """Check if Band/Redis is available"""
        try:
            if not self.redis:
                self.healthy = False
                return False
            
            # Try a simple PING
            response = await asyncio.wait_for(self.redis.ping(), timeout=5)
            self.healthy = response is True
            return self.healthy
        
        except Exception as e:
            logger.warning(f"Band health check failed: {e}")
            self.healthy = False
            return False
    
    async def cleanup(self):
        """Cleanup all subscriptions"""
        for subscription_id in list(self.subscriptions.keys()):
            await self.unsubscribe(subscription_id)