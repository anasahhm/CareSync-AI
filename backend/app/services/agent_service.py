"""
Agent Service Layer

High-level service for agent-based consultation processing.
Handles initialization, orchestration, and result formatting.
"""
import logging
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import AgentContext
from app.communication import (
    AgentCommunicationLayer, LocalEventBus
)
from app.core.config import settings
from app.core.socketio_app import sio
from app.orchestration import ConsultationOrchestrator, get_agent_registry
from app.memory import MemoryManager
from app.rag import RAGManager
from app.vision import VisionManager
from app.gpu import GPUManager

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service layer for agent-based consultation processing.
    Manages orchestration and provides clean API.
    """
    
    _instance: Optional['AgentService'] = None
    _initialized = False
    
    def __init__(self):
        self.communication_layer: Optional[AgentCommunicationLayer] = None
        self.agent_registry = None
        self.memory_manager: Optional[MemoryManager] = None
        self.rag_manager: Optional[RAGManager] = None
        self.vision_manager: Optional[VisionManager] = None
        self.gpu_manager: Optional[GPUManager] = None
    
    @classmethod
    async def get_instance(cls) -> 'AgentService':
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            if not cls._initialized:
                await cls._instance._initialize()
                cls._initialized = True
        return cls._instance
    
    async def _initialize(self):
        """Initialize communication and agents"""
        try:
            # Create local event bus with Socket.IO for real-time updates
            local_bus = LocalEventBus(sio_server=sio)
            
            # Create communication layer with fallback
            self.communication_layer = AgentCommunicationLayer(
                primary_bus=local_bus,
                fallback_bus=local_bus  # Same bus serves both roles for hackathon
            )
            
            # Start communication layer
            await self.communication_layer.start()
            
            # Initialize agents
            self.agent_registry = await get_agent_registry(self.communication_layer)

            # Initialize memory layer (Redis-backed, auto-fallback to in-process)
            self.memory_manager = MemoryManager(settings.REDIS_URL)
            await self.memory_manager.initialize()

            # Initialize RAG layer (Qdrant-backed, auto-fallback to in-memory FAISS)
            self.rag_manager = RAGManager(
                qdrant_url=settings.QDRANT_URL,
                ollama_url=settings.OLLAMA_URL,
                enable_pubmed=settings.RAG_ENABLE_PUBMED,
                redis_cache=self.memory_manager.cache,
            )
            await self.rag_manager.initialize()

            # Give RAG-aware agents a reference (agents that don't define
            # this attribute are unaffected - see BaseAgent.rag default None)
            for agent in self.agent_registry.get_all_agents().values():
                agent.rag = self.rag_manager

            # Initialize vision layer (MediaPipe/OpenCV, degrades gracefully
            # to available=False per-detector if libraries/models are missing)
            self.vision_manager = VisionManager(
                communication_layer=self.communication_layer,
                memory_manager=self.memory_manager,
            )
            for agent in self.agent_registry.get_all_agents().values():
                agent.vision = self.vision_manager

            # Initialize GPU/ROCm layer (auto-detects ROCm/CUDA/CPU; CPU-only
            # environments - like this one - get a fully valid CPU result)
            self.gpu_manager = GPUManager(
                backend=settings.GPU_BACKEND,
                ollama_url=settings.OLLAMA_URL,
                ollama_fallback_model=settings.OLLAMA_FALLBACK_MODEL,
            )
            await self.gpu_manager.initialize()

            logger.info("AgentService initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize AgentService: {e}")
            raise
    
    async def process_consultation(
        self,
        consultation_id: str,
        patient_id: str,
        doctor_id: Optional[str],
        chief_complaint: Optional[str],
        doctor_notes: Optional[str],
        medical_history: Dict[str, Any],
        annotations: list,
        gesture_events: list,
        patient_allergies: list,
        patient_medications: list,
        patient_age: Optional[int],
        insurance_plan: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process consultation through agent system.
        
        Returns: {
            status: COMPLETED|FAILED,
            duration_seconds: float,
            agent_results: {...},
            consensus: {...},
            final_recommendations: [...],
            escalations: [...]
        }
        """
        
        try:
            # Create context for agents
            context = AgentContext(
                consultation_id=consultation_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                chief_complaint=chief_complaint,
                doctor_notes=doctor_notes,
                medical_history=medical_history,
                annotations=annotations,
                gesture_events=gesture_events,
                patient_allergies=patient_allergies,
                patient_current_medications=patient_medications,
                patient_age=patient_age,
                insurance_plan=insurance_plan
            )
            
            # Create orchestrator
            orchestrator = ConsultationOrchestrator(
                agents=self.agent_registry.get_all_agents(),
                communication_layer=self.communication_layer,
                db=db,
                memory_manager=self.memory_manager
            )
            
            # Process consultation
            result = await orchestrator.process_consultation(consultation_id, context)

            if self.memory_manager and result.get("status") == "COMPLETED":
                try:
                    patient_memory = self.memory_manager.patient_memory_for(db)
                    consensus = result.get("consensus", {})
                    await patient_memory.record_consultation_summary(
                        patient_id=patient_id,
                        consultation_id=consultation_id,
                        primary_diagnosis=consensus.get("primary_diagnosis"),
                        risk_score=consensus.get("overall_risk_score", 0.0)
                    )
                except Exception as e:
                    logger.warning(f"Could not record patient memory summary: {e}")

            return result
        
        except Exception as e:
            logger.error(f"Consultation processing failed: {e}")
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        agents = self.agent_registry.get_all_agents() if self.agent_registry else {}
        
        return {
            "initialized": self._initialized,
            "agent_count": len(agents),
            "agents": {
                agent_type: {
                    "type": agent.AGENT_TYPE,
                    "description": agent.AGENT_DESCRIPTION,
                    "dependencies": agent.DEPENDENCIES
                }
                for agent_type, agent in agents.items()
            },
            "communication_healthy": (
                await self.communication_layer.health_check()
                if self.communication_layer else False
            )
        }
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.communication_layer:
            await self.communication_layer.stop()
        if self.memory_manager:
            await self.memory_manager.shutdown()
        logger.info("AgentService shutdown")


# Convenience function to get service instance
async def get_agent_service() -> AgentService:
    """Get agent service instance"""
    return await AgentService.get_instance()

async def shutdown_agent_registry():
    """Shutdown agent service and cleanup resources"""
    if AgentService._instance is not None:
        try:
            await AgentService._instance.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down agent service: {e}")

        AgentService._instance = None
        AgentService._initialized = False