"""
Chief Orchestrator Agent

Runs first in the pipeline. Classifies case complexity/pathway and publishes
routing guidance that other agents (and the workflow coordinator) can use.
This is distinct from ConsultationOrchestrator (the code that schedules agent
execution) - this agent contributes a *clinical* opinion on how the case
should be routed, and participates in consensus like every other agent.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class ChiefOrchestratorAgent(BaseAgent):
    AGENT_TYPE = "CHIEF_ORCHESTRATOR"
    AGENT_DESCRIPTION = "Classifies case complexity and sets the care pathway for downstream agents"
    DEPENDENCIES = []
    TIMEOUT_SECONDS = 8

    COMPLEX_SIGNALS = [
        "multiple", "chronic", "recurring", "unclear", "worsening",
        "several", "long-standing", "complicated",
    ]
    SIMPLE_SIGNALS = ["mild", "minor", "single", "brief", "isolated"]

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        complaint = (context.chief_complaint or "").lower()
        notes = (context.doctor_notes or "").lower()
        text = f"{complaint} {notes}"

        complexity_score = sum(1 for s in self.COMPLEX_SIGNALS if s in text)
        simplicity_score = sum(1 for s in self.SIMPLE_SIGNALS if s in text)

        history_depth = len(context.medical_history or {})
        medication_count = len(context.patient_current_medications or [])

        vision_distress_boost = 0
        if self.vision:
            try:
                observation = self.vision.get_latest_observation(context.consultation_id)
                if observation and observation.get("summary", {}).get("distress_flags"):
                    vision_distress_boost = 1
            except Exception as e:
                self.logger.warning(f"ChiefOrchestratorAgent: could not read vision observation (non-fatal): {e}")

        weighted_complexity = complexity_score + (history_depth > 3) + (medication_count > 2) - simplicity_score + vision_distress_boost

        if weighted_complexity >= 3:
            pathway = "COMPLEX_MULTI_SPECIALTY"
            priority = "HIGH"
        elif weighted_complexity >= 1:
            pathway = "STANDARD_REVIEW"
            priority = "MEDIUM"
        else:
            pathway = "FAST_TRACK"
            priority = "LOW"

        recommendations.append({
            "type": "care_pathway",
            "text": f"Case routed as {pathway.replace('_', ' ').title()}",
            "confidence": 0.75,
            "priority": priority,
            "evidence": [
                f"complexity_signals={complexity_score}",
                f"simplicity_signals={simplicity_score}",
                f"history_depth={history_depth}",
                f"active_medications={medication_count}",
            ],
        })

        if pathway == "COMPLEX_MULTI_SPECIALTY":
            escalations.append({
                "level": "MEDIUM",
                "reason": "Case complexity suggests multi-specialty input may be required",
                "type": "routing_notice",
                "action": "Flag for senior physician review before final sign-off",
            })

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {"pathway": pathway, "weighted_complexity": weighted_complexity},
            "confidence": 0.75,
        }
