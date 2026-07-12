"""
Hallucination Detection Agent

Reviews every recommendation published in this consultation and flags ones
that look unreliable: no evidence attached, confidence claimed higher than
the evidence supports, or contradictory claims between agents. This does not
call an external LLM judge (no paid APIs) - it applies deterministic
heuristics, which is intentionally conservative (some false positives are
preferable to silently trusting ungrounded claims in a medical context).
"""
import logging
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE_THRESHOLD = 0.85
MIN_EVIDENCE_FOR_HIGH_CONFIDENCE = 1


class HallucinationDetectionAgent(BaseAgent):
    AGENT_TYPE = "HALLUCINATION_DETECTION"
    AGENT_DESCRIPTION = "Flags unsupported or overconfident claims across all agent outputs"
    DEPENDENCIES = ["MEDICAL_RESEARCH", "EVIDENCE", "TREATMENT_RECOMMENDATION", "DIAGNOSTIC"]
    TIMEOUT_SECONDS = 12

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        all_recs = await self._collect_all_recommendations(context)

        flagged: List[Dict[str, Any]] = []
        for rec in all_recs:
            confidence = rec.get("confidence", 0.7)
            evidence = rec.get("evidence", [])
            reasons = []

            if confidence >= HIGH_CONFIDENCE_THRESHOLD and len(evidence) < MIN_EVIDENCE_FOR_HIGH_CONFIDENCE:
                reasons.append("high confidence claimed without sufficient evidence")

            text = (rec.get("text") or "").strip()
            if not text:
                reasons.append("empty claim text")

            if reasons:
                flagged.append({"claim": text, "source": rec.get("source_agent", "unknown"), "reasons": reasons})

        contradictions = self._detect_contradictions(all_recs)

        if flagged:
            recommendations.append({
                "type": "hallucination_review",
                "text": f"{len(flagged)} claim(s) flagged as potentially ungrounded",
                "confidence": 0.8,
                "priority": "HIGH" if len(flagged) > 2 else "MEDIUM",
                "evidence": [f"{f['source']}: {f['claim']} ({'; '.join(f['reasons'])})" for f in flagged[:10]],
            })
            escalations.append({
                "level": "MEDIUM",
                "reason": f"{len(flagged)} potentially ungrounded claim(s) detected",
                "type": "hallucination_flag",
                "action": "Require Quality Assurance and human clinician review before finalizing",
            })
        else:
            recommendations.append({
                "type": "hallucination_review",
                "text": "No ungrounded claims detected in current recommendation set",
                "confidence": 0.7,
                "priority": "LOW",
                "evidence": [f"reviewed {len(all_recs)} recommendations"],
            })

        if contradictions:
            escalations.append({
                "level": "MEDIUM",
                "reason": "Contradictory recommendations detected between agents",
                "type": "contradiction_flag",
                "action": "Route to Consensus Moderator for resolution",
            })

        confidence = 0.9 if not flagged and not contradictions else 0.5

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {
                "flagged_count": len(flagged),
                "contradiction_count": len(contradictions),
                "total_reviewed": len(all_recs),
            },
            "confidence": confidence,
        }

    async def _collect_all_recommendations(self, context: AgentContext) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=200)
            for event in history:
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = dict(event.payload.get("recommendation", {}))
                    rec["source_agent"] = event.payload.get("agent_type", event.source_agent)
                    recs.append(rec)
        except Exception as e:
            self.logger.warning(f"Could not read recommendation history: {e}")
        return recs

    def _detect_contradictions(self, recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        treatment_texts = {r.get("text") for r in recs if r.get("type") == "treatment_plan" and r.get("text")}
        contradictions = []
        if len(treatment_texts) > 2:
            contradictions.append({"type": "treatment_divergence", "count": len(treatment_texts)})
        return contradictions
