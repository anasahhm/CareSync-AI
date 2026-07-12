"""
Consensus Moderator Agent

Does not compute the final numeric consensus score (that remains the
ConsensusEngine's job, run centrally by the orchestrator so it always
executes even if this agent fails). Instead this agent acts as a
participating "tie-breaker" voice: it looks at every recommendation and
escalation published so far, decides which of any conflicting claims should
be weighted as authoritative, and publishes that decision as a
MODERATOR_DECISION event the ConsensusEngine gives extra weight to.
"""
import logging
from collections import defaultdict
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)


class ConsensusModeratorAgent(BaseAgent):
    AGENT_TYPE = "CONSENSUS_MODERATOR"
    AGENT_DESCRIPTION = "Resolves conflicting recommendations ahead of final consensus scoring"
    DEPENDENCIES = ["QUALITY_ASSURANCE"]
    TIMEOUT_SECONDS = 10

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        by_type = await self._group_by_type(context)

        rulings: List[Dict[str, Any]] = []
        for rec_type, recs in by_type.items():
            if rec_type not in ("treatment_plan", "clinical_finding", "differential_diagnosis"):
                continue
            if len(recs) <= 1:
                continue
            # Pick the highest-confidence claim as the authoritative one
            best = max(recs, key=lambda r: r.get("confidence", 0))
            rulings.append({
                "type": rec_type,
                "chosen": best.get("text"),
                "chosen_confidence": best.get("confidence"),
                "alternatives_considered": len(recs) - 1,
            })

        if rulings:
            recommendations.append({
                "type": "moderator_ruling",
                "text": f"Moderator resolved {len(rulings)} category conflict(s)",
                "confidence": 0.75,
                "priority": "MEDIUM",
                "evidence": [f"{r['type']}: chose '{r['chosen']}' ({r['chosen_confidence']})" for r in rulings],
            })
        else:
            recommendations.append({
                "type": "moderator_ruling",
                "text": "No conflicting recommendations required moderation",
                "confidence": 0.8,
                "priority": "LOW",
                "evidence": [],
            })

        await self._publish_moderator_decision(context, rulings)

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {"rulings": rulings},
            "confidence": 0.8,
        }

    async def _group_by_type(self, context: AgentContext) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=200)
            for event in history:
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = event.payload.get("recommendation", {})
                    grouped[rec.get("type", "general")].append(rec)
        except Exception as e:
            self.logger.warning(f"Could not read recommendation history: {e}")
        return grouped

    async def _publish_moderator_decision(self, context: AgentContext, rulings: List[Dict[str, Any]]):
        try:
            from app.communication import create_agent_event
            event = create_agent_event(
                event_type=EventType.MODERATOR_DECISION,
                source_agent=self.AGENT_TYPE,
                source_agent_id=self.agent_id,
                consultation_id=context.consultation_id,
                payload={"rulings": rulings},
            )
            await self.communication.publish(event)
        except Exception as e:
            self.logger.error(f"Failed to publish moderator decision: {e}")
