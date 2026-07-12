"""
Local Event Bus

In-memory event bus for agent communication.
Used as fallback when Band SDK is unavailable.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Set
from uuid import uuid4

from . import (
    AgentEvent,
    EventType,
    AgentCommunicationBus
)

logger = logging.getLogger(__name__)


class LocalEventBus(AgentCommunicationBus):
    """
    In-memory event bus using asyncio.Event and Queue.
    Perfect for fallback and testing.
    Emits events to Socket.IO for real-time frontend updates.
    """
    
    def __init__(self, sio_server=None):
        # Structure: {(event_type, consultation_id): [events]}
        self.event_history: Dict[tuple, List[AgentEvent]] = {}
        
        # Structure: {subscription_id: (event_type, consultation_id, callback)}
        self.subscriptions: Dict[str, tuple] = {}
        
        # Structure: {subscription_id: asyncio.Event}
        self.event_signals: Dict[str, asyncio.Event] = {}
        
        # Structure: {(event_type, consultation_id): Set[subscription_ids]}
        self.subscription_index: Dict[tuple, Set[str]] = {}
        
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
        
        # Socket.IO server for real-time frontend updates
        self.sio_server = sio_server
        
        self.healthy = True
    
    async def publish(self, event: AgentEvent) -> bool:
        """Publish an event to all subscribers and emit via Socket.IO"""
        try:
            async with self.lock:
                # Store in history
                key = (event.event_type, event.consultation_id)
                if key not in self.event_history:
                    self.event_history[key] = []
                self.event_history[key].append(event)
                
                # Keep only last 1000 events per (type, consultation)
                if len(self.event_history[key]) > 1000:
                    self.event_history[key].pop(0)
            
            # Emit to Socket.IO for real-time frontend updates
            if self.sio_server:
                try:
                    room = f"consultation:{event.consultation_id}"
                    event_data = {
                        "agent_type": event.source_agent,
                        "event_type": str(event.event_type),
                        "timestamp": event.timestamp.isoformat(),
                        "data": event.data
                    }
                    await self.sio_server.emit(
                        f"agent:{event.event_type.value}",
                        event_data,
                        room=room
                    )
                except Exception as sio_error:
                    logger.debug(f"Socket.IO emit failed (non-critical): {sio_error}")
            
            # Notify all subscribers for this event type + consultation
            if key in self.subscription_index:
                for subscription_id in self.subscription_index[key]:
                    if subscription_id in self.event_signals:
                        self.event_signals[subscription_id].set()
                    
                    # Also call callback if exists
                    if subscription_id in self.subscriptions:
                        event_type, consultation_id, callback = self.subscriptions[subscription_id]
                        try:
                            # Fire and forget callback
                            asyncio.create_task(self._run_callback(callback, event))
                        except Exception as e:
                            logger.error(f"Callback error for subscription {subscription_id}: {e}")
            
            logger.debug(f"Published event: {event.event_type} from {event.source_agent}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    async def _run_callback(self, callback, event):
        """Run callback safely"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"Callback execution error: {e}")
    
    async def subscribe(
        self,
        event_type: EventType,
        consultation_id: str,
        callback: Optional[Callable] = None
    ) -> str:
        """Subscribe to events"""
        subscription_id = str(uuid4())
        
        async with self.lock:
            key = (event_type, consultation_id)
            
            # Store subscription
            self.subscriptions[subscription_id] = (event_type, consultation_id, callback)
            
            # Create event signal
            self.event_signals[subscription_id] = asyncio.Event()
            
            # Index subscription
            if key not in self.subscription_index:
                self.subscription_index[key] = set()
            self.subscription_index[key].add(subscription_id)
        
        logger.debug(f"Subscribed to {event_type} for consultation {consultation_id}")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        try:
            async with self.lock:
                if subscription_id in self.subscriptions:
                    event_type, consultation_id, _ = self.subscriptions[subscription_id]
                    del self.subscriptions[subscription_id]
                    
                    # Remove from index
                    key = (event_type, consultation_id)
                    if key in self.subscription_index:
                        self.subscription_index[key].discard(subscription_id)
                    
                    # Remove signal
                    if subscription_id in self.event_signals:
                        del self.event_signals[subscription_id]
                    
                    logger.debug(f"Unsubscribed: {subscription_id}")
                    return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False
    
    async def wait_for_event(
        self,
        event_type: EventType,
        consultation_id: str,
        timeout_seconds: int = 30,
        filter_fn: Optional[Callable] = None
    ) -> Optional[AgentEvent]:
        """Wait for a specific event"""
        subscription_id = await self.subscribe(event_type, consultation_id)
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check history first
                key = (event_type, consultation_id)
                async with self.lock:
                    if key in self.event_history:
                        # Find matching event
                        for event in reversed(self.event_history[key]):
                            if filter_fn is None or filter_fn(event):
                                return event
                
                # Wait for new events
                event_signal = self.event_signals.get(subscription_id)
                if not event_signal:
                    return None
                
                # Calculate remaining timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                remaining = timeout_seconds - elapsed
                
                if remaining <= 0:
                    return None
                
                try:
                    await asyncio.wait_for(event_signal.wait(), timeout=remaining)
                    event_signal.clear()
                except asyncio.TimeoutError:
                    return None
        
        finally:
            await self.unsubscribe(subscription_id)
    
    async def get_event_history(
        self,
        consultation_id: str,
        limit: int = 100
    ) -> List[AgentEvent]:
        """Get event history for a consultation"""
        try:
            async with self.lock:
                all_events = []
                
                # Collect events for all types for this consultation
                for (event_type, cons_id), events in self.event_history.items():
                    if cons_id == consultation_id:
                        all_events.extend(events)
                
                # Sort by timestamp, most recent first
                all_events.sort(key=lambda e: e.timestamp, reverse=True)
                
                return all_events[:limit]
        
        except Exception as e:
            logger.error(f"Failed to get event history: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check bus health"""
        return self.healthy
    
    async def clear(self):
        """Clear all events (for testing)"""
        async with self.lock:
            self.event_history.clear()
            self.subscriptions.clear()
            self.event_signals.clear()
            self.subscription_index.clear()
        logger.info("LocalEventBus cleared")