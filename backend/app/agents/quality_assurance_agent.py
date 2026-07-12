"""
Quality Assurance Agent

Gate-checks the consultation before it reaches the Consensus Moderator:
did every expected agent report in, was a diagnosis produced, were
escalations acknowledged, and did the Hallucination Detection Agent
clear the recommendation set (or at least flag it for review).
"""
import logging
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)

EXPECTED_CORE_AGENTS = [
    "CLINICAL_REVIEW", "DIAGNOSTIC", "TREATMENT_RECOMMENDATION", "HALLUCINATION_DETECTION",
]


class QualityAssuranceAgent(BaseAgent):
    AGENT_TYPE = "QUALITY_ASSURANCE"
    AGENT_DESCRIPTION = "Checks completeness and safety gates before consensus finalization"
    DEPENDENCIES = ["HALLUCINATION_DETECTION"]
    TIMEOUT_SECONDS = 10

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        completed_agents = await self._get_completed_agents(context)
        missing = [a for a in EXPECTED_CORE_AGENTS if a not in completed_agents]

        hallucination_clear = await self._hallucination_status(context)

        checks = {
            "core_agents_complete": not missing,
            "hallucination_review_clear": hallucination_clear,
            "diagnosis_present": "DIAGNOSTIC" in completed_agents,
        }

        passed = all(checks.values())

        recommendations.append({
            "type": "qa_gate",
            "text": "QA gate PASSED - consultation ready for consensus" if passed else "QA gate FAILED - issues found before consensus",
            "confidence": 0.85 if passed else 0.6,
            "priority": "LOW" if passed else "HIGH",
            "evidence": [f"{k}={v}" for k, v in checks.items()],
        })

        if missing:
            escalations.append({
                "level": "MEDIUM",
                "reason": f"Missing expected agent output(s): {', '.join(missing)}",
                "type": "qa_completeness",
                "action": "Do not finalize until missing agents complete or are explicitly waived",
            })

        if not hallucination_clear:
            escalations.append({
                "level": "MEDIUM",
                "reason": "Hallucination review flagged issues that are unresolved",
                "type": "qa_safety_gate",
                "action": "Require clinician sign-off before releasing recommendations to patient",
            })

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {"checks": checks, "missing_agents": missing},
            "confidence": 0.85 if passed else 0.55,
        }

    async def _get_completed_agents(self, context: AgentContext) -> List[str]:
        completed = set()
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=200)
            for event in history:
                if event.event_type == EventType.AGENT_COMPLETED:
                    completed.add(event.payload.get("agent_type"))
        except Exception as e:
            self.logger.warning(f"Could not read agent completion history: {e}")
        return list(completed)

    async def _hallucination_status(self, context: AgentContext) -> bool:
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=200)
            for event in reversed(history):
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = event.payload.get("recommendation", {})
                    if rec.get("type") == "hallucination_review":
                        return "No ungrounded claims" in (rec.get("text") or "")
        except Exception as e:
            self.logger.warning(f"Could not read hallucination review status: {e}")
        return True
