"""
Base Agent Class

Foundation for all healthcare agents in the Band of Agents system.
Handles event publishing, dependency management, error handling, and auditability.
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from app.communication import (
    AgentCommunicationLayer, EventType, create_agent_event
)

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to agents containing consultation data"""
    consultation_id: str
    patient_id: str
    doctor_id: Optional[str]
    chief_complaint: Optional[str]
    doctor_notes: Optional[str]
    medical_history: Dict[str, Any]
    annotations: List[Dict[str, Any]]
    gesture_events: List[Dict[str, Any]]
    patient_allergies: List[str]
    patient_current_medications: List[str]
    patient_age: Optional[int]
    insurance_plan: Optional[str]
    # Previous agent outputs available
    previous_recommendations: Dict[str, Any] = None


class BaseAgent(ABC):
    """
    Base class for all healthcare agents.
    Provides common infrastructure for event publishing, logging, dependencies.
    """
    
    AGENT_TYPE: str = "BASE_AGENT"
    AGENT_DESCRIPTION: str = "Base agent class"
    DEPENDENCIES: List[str] = []  # List of agent types this agent depends on
    TIMEOUT_SECONDS: int = 30
    
    def __init__(self, communication_layer: AgentCommunicationLayer):
        self.agent_id = str(uuid4())
        self.communication = communication_layer
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.rag = None  # injected post-construction by AgentService once RAGManager is ready
        self.vision = None  # injected post-construction by AgentService once VisionManager is ready
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Main execution method.
        Returns: {status, recommendations, escalations, metadata}
        """
        start_time = time.time()
        execution_result = {
            "agent_type": self.AGENT_TYPE,
            "agent_id": self.agent_id,
            "status": "PENDING",
            "recommendations": [],
            "escalations": [],
            "metadata": {},
            "duration_ms": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Publish agent started event
            await self._publish_event(
                EventType.AGENT_STARTED,
                context.consultation_id,
                {"agent_type": self.AGENT_TYPE}
            )
            
            # Wait for dependencies
            await self._wait_for_dependencies(context.consultation_id)
            
            # Publish agent processing event
            await self._publish_event(
                EventType.AGENT_PROCESSING,
                context.consultation_id,
                {"agent_type": self.AGENT_TYPE}
            )
            
            # Execute agent logic
            agent_output = await self._run(context)
            
            # Extract recommendations and escalations
            recommendations = agent_output.get("recommendations", [])
            escalations = agent_output.get("escalations", [])
            
            # Publish recommendations
            for rec in recommendations:
                await self._publish_recommendation(context.consultation_id, rec)
            
            # Publish escalations if any
            for escal in escalations:
                await self._publish_escalation(context.consultation_id, escal)
            
            # Publish completion event
            await self._publish_event(
                EventType.AGENT_COMPLETED,
                context.consultation_id,
                {
                    "agent_type": self.AGENT_TYPE,
                    "recommendation_count": len(recommendations),
                    "escalation_count": len(escalations)
                }
            )
            
            execution_result.update({
                "status": "COMPLETED",
                "recommendations": recommendations,
                "escalations": escalations,
                "metadata": agent_output.get("metadata", {}),
                "confidence": agent_output.get("confidence", 0.7)
            })
        
        except asyncio.TimeoutError:
            self.logger.error(f"Agent {self.AGENT_TYPE} execution timeout")
            execution_result["status"] = "FAILED"
            execution_result["error"] = "TIMEOUT"
            await self._publish_event(
                EventType.AGENT_FAILED,
                context.consultation_id,
                {"agent_type": self.AGENT_TYPE, "error": "TIMEOUT"}
            )
        
        except Exception as e:
            self.logger.error(f"Agent {self.AGENT_TYPE} execution error: {e}")
            execution_result["status"] = "FAILED"
            execution_result["error"] = str(e)
            await self._publish_event(
                EventType.AGENT_FAILED,
                context.consultation_id,
                {"agent_type": self.AGENT_TYPE, "error": str(e)}
            )
        
        finally:
            # Always record duration
            execution_result["duration_ms"] = int((time.time() - start_time) * 1000)
        
        return execution_result
    
    @abstractmethod
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """
        Agent-specific logic.
        
        Must return dict with:
        {
            "recommendations": [
                {
                    "type": str,
                    "text": str,
                    "confidence": float,
                    "priority": "LOW|MEDIUM|HIGH|CRITICAL",
                    "evidence": [str]
                },
                ...
            ],
            "escalations": [
                {
                    "level": "LOW|MEDIUM|HIGH|CRITICAL",
                    "reason": str,
                    "type": str,
                    "action": str
                },
                ...
            ],
            "metadata": {...},
            "confidence": float (0-1)
        }
        """
        pass
    
    async def _wait_for_dependencies(self, consultation_id: str):
        """Wait for all dependency agents to complete"""
        if not self.DEPENDENCIES:
            return
        
        # Wait for each dependency
        for dependency_agent_type in self.DEPENDENCIES:
            try:
                event = await self.communication.wait_for_event(
                    EventType.AGENT_COMPLETED,
                    consultation_id,
                    timeout_seconds=self.TIMEOUT_SECONDS,
                    filter_fn=lambda e: e.payload.get("agent_type") == dependency_agent_type
                )
                if not event:
                    self.logger.warning(f"Dependency {dependency_agent_type} did not complete in time")
            except Exception as e:
                self.logger.warning(f"Error waiting for dependency {dependency_agent_type}: {e}")
    
    async def _publish_event(self, event_type: EventType, consultation_id: str, payload: Dict):
        """Publish an agent event"""
        try:
            event = create_agent_event(
                event_type=event_type,
                source_agent=self.AGENT_TYPE,
                source_agent_id=self.agent_id,
                consultation_id=consultation_id,
                payload=payload
            )
            await self.communication.publish(event)
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
    
    async def _publish_recommendation(self, consultation_id: str, recommendation: Dict):
        """Publish a recommendation"""
        try:
            await self._publish_event(
                EventType.RECOMMENDATION_AVAILABLE,
                consultation_id,
                {
                    "agent_type": self.AGENT_TYPE,
                    "recommendation": recommendation
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to publish recommendation: {e}")
    
    async def _publish_escalation(self, consultation_id: str, escalation: Dict):
        """Publish an escalation"""
        try:
            await self._publish_event(
                EventType.ESCALATION_REQUIRED,
                consultation_id,
                {
                    "agent_type": self.AGENT_TYPE,
                    "escalation": escalation
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to publish escalation: {e}")


class AgentConfig:
    """Configuration for agent execution"""
    max_retries: int = 2
    timeout_seconds: int = 30
    enable_caching: bool = True
    debug_mode: bool = False