"""
Escalation Agent

Final safety-net escalation authority. Distinct from the Triage & Escalation
Agent (which makes an early ESI-style urgency call from the raw complaint).
This agent runs last-but-one, after the Consensus Moderator, and aggregates
every escalation raised by any agent during the run to decide whether the
case as a whole needs to be pulled out of the automated pipeline for
mandatory human review before anything reaches the patient.
"""
import logging
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)

LEVEL_WEIGHT = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


class EscalationAgent(BaseAgent):
    AGENT_TYPE = "ESCALATION"
    AGENT_DESCRIPTION = "Aggregates all escalations raised during the run and makes the final human-review call"
    DEPENDENCIES = ["CONSENSUS_MODERATOR"]
    TIMEOUT_SECONDS = 8

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        all_escalations = await self._collect_escalations(context)
        total_weight = sum(LEVEL_WEIGHT.get(e.get("level", "LOW"), 1) for e in all_escalations)
        max_level = max((e.get("level", "LOW") for e in all_escalations), key=lambda l: LEVEL_WEIGHT.get(l, 1), default="LOW")

        requires_human_review = total_weight >= 5 or max_level in ("HIGH", "CRITICAL")

        recommendations.append({
            "type": "final_escalation_summary",
            "text": (
                f"Mandatory human review required (aggregate escalation weight={total_weight}, peak={max_level})"
                if requires_human_review
                else f"No mandatory human review trigger (aggregate escalation weight={total_weight}, peak={max_level})"
            ),
            "confidence": 0.85,
            "priority": "CRITICAL" if requires_human_review else "LOW",
            "evidence": [f"{e.get('type')}:{e.get('level')} - {e.get('reason')}" for e in all_escalations[:15]],
        })

        if requires_human_review:
            escalations.append({
                "level": max_level,
                "reason": "Aggregate escalation signal across agents exceeded safe-automation threshold",
                "type": "final_human_review_required",
                "action": "Hold report from patient-facing release until a clinician reviews and signs off",
            })

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {
                "total_escalations_seen": len(all_escalations),
                "aggregate_weight": total_weight,
                "peak_level": max_level,
                "requires_human_review": requires_human_review,
            },
            "confidence": 0.85,
        }

    async def _collect_escalations(self, context: AgentContext) -> List[Dict[str, Any]]:
        escalations: List[Dict[str, Any]] = []
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=200)
            for event in history:
                if event.event_type == EventType.ESCALATION_REQUIRED:
                    escalations.append(event.payload.get("escalation", {}))
        except Exception as e:
            self.logger.warning(f"Could not read escalation history: {e}")
        return escalations
