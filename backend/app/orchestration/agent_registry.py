"""
Agent Registry

Manages agent lifecycle, initialization, and lookup.
Provides factory for creating agent instances.
"""
import logging
from typing import Dict, Optional

from app.agents import BaseAgent
from app.agents.clinical_review_agent import ClinicalReviewAgent
from app.agents.medical_history_agent import MedicalHistoryAgent
from app.agents.compliance_privacy_agent import CompliancePrivacyAgent
from app.agents.triage_escalation_agent import TriageEscalationAgent
from app.agents.treatment_recommendation_agent import TreatmentRecommendationAgent
from app.agents.insurance_verification_agent import InsuranceVerificationAgent
from app.agents.followup_coordination_agent import FollowupCoordinationAgent
from app.agents.chief_orchestrator_agent import ChiefOrchestratorAgent
from app.agents.symptom_agent import SymptomAgent
from app.agents.diagnostic_agent import DiagnosticAgent
from app.agents.medical_research_agent import MedicalResearchAgent
from app.agents.evidence_agent import EvidenceAgent
from app.agents.hallucination_detection_agent import HallucinationDetectionAgent
from app.agents.quality_assurance_agent import QualityAssuranceAgent
from app.agents.consensus_moderator_agent import ConsensusModeratorAgent
from app.agents.explanation_agent import ExplanationAgent
from app.agents.escalation_agent import EscalationAgent
from app.communication import AgentCommunicationLayer

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for all agents.
    Handles initialization, lifecycle, and lookup.
    """
    
    # Mapping of agent types to classes
    AGENT_CLASSES = {
        "CLINICAL_REVIEW": ClinicalReviewAgent,
        "MEDICAL_HISTORY": MedicalHistoryAgent,
        "COMPLIANCE_PRIVACY": CompliancePrivacyAgent,
        "TRIAGE_ESCALATION": TriageEscalationAgent,
        "TREATMENT_RECOMMENDATION": TreatmentRecommendationAgent,
        "INSURANCE_VERIFICATION": InsuranceVerificationAgent,
        "FOLLOWUP_COORDINATION": FollowupCoordinationAgent,
        # Extended V2 roster
        "CHIEF_ORCHESTRATOR": ChiefOrchestratorAgent,
        "SYMPTOM": SymptomAgent,
        "DIAGNOSTIC": DiagnosticAgent,
        "MEDICAL_RESEARCH": MedicalResearchAgent,
        "EVIDENCE": EvidenceAgent,
        "HALLUCINATION_DETECTION": HallucinationDetectionAgent,
        "QUALITY_ASSURANCE": QualityAssuranceAgent,
        "CONSENSUS_MODERATOR": ConsensusModeratorAgent,
        "EXPLANATION": ExplanationAgent,
        "ESCALATION": EscalationAgent,
    }
    
    def __init__(self, communication_layer: AgentCommunicationLayer):
        self.communication = communication_layer
        self.agents: Dict[str, BaseAgent] = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize all agents"""
        for agent_type, agent_class in self.AGENT_CLASSES.items():
            try:
                agent = agent_class(self.communication)
                self.agents[agent_type] = agent
                logger.info(f"Initialized agent: {agent_type}")
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent_type}: {e}")
        
        self.initialized = True
        logger.info(f"Agent registry initialized with {len(self.agents)} agents")
    
    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """Get agent by type"""
        return self.agents.get(agent_type)
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """Get all agents"""
        return self.agents.copy()
    
    def list_agent_types(self) -> list:
        """List all registered agent types"""
        return list(self.AGENT_CLASSES.keys())
    
    async def shutdown(self):
        """Shutdown all agents"""
        self.agents.clear()
        logger.info("Agent registry shutdown")


# Global registry instance
_agent_registry: Optional[AgentRegistry] = None


async def get_agent_registry(communication_layer: Optional[AgentCommunicationLayer] = None) -> AgentRegistry:
    """Get or create global agent registry"""
    global _agent_registry
    
    if _agent_registry is None:
        if communication_layer is None:
            raise RuntimeError("Communication layer required to initialize registry")
        
        _agent_registry = AgentRegistry(communication_layer)
        await _agent_registry.initialize()
    
    return _agent_registry


async def shutdown_agent_registry():
    """Shutdown global agent registry"""
    global _agent_registry
    if _agent_registry:
        await _agent_registry.shutdown()
        _agent_registry = None