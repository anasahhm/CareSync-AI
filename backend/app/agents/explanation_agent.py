"""
Explanation Agent

Translates the moderator-approved clinical recommendations into a short,
plain-language explanation suitable for the patient-facing report. Runs
after the Consensus Moderator so it explains the resolved view, not raw
per-agent noise.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)

JARGON_SIMPLIFICATIONS = {
    "acute coronary syndrome": "a possible heart-related cause",
    "gastroenteritis": "a stomach bug",
    "cellulitis": "a skin infection",
    "musculoskeletal": "muscle or joint related",
    "differential diagnosis": "possible explanations",
}


class ExplanationAgent(BaseAgent):
    AGENT_TYPE = "EXPLANATION"
    AGENT_DESCRIPTION = "Translates finalized recommendations into plain-language patient explanations"
    DEPENDENCIES = ["CONSENSUS_MODERATOR"]
    TIMEOUT_SECONDS = 8

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        top_finding, treatment = await self._get_key_outputs(context)

        plain_finding = self._simplify(top_finding) if top_finding else "your symptoms are still being evaluated"
        plain_treatment = self._simplify(treatment) if treatment else "your care team will confirm next steps"

        vision_note = ""
        if self.vision:
            try:
                observation = self.vision.get_latest_observation(context.consultation_id)
                if observation and observation.get("summary", {}).get("pain_score", 0) > 0.5:
                    vision_note = " The visit also noted signs of discomfort that were factored into this assessment."
            except Exception as e:
                self.logger.warning(f"ExplanationAgent: could not read vision observation (non-fatal): {e}")

        explanation = (
            f"Based on what was shared, the care team believes {plain_finding}. "
            f"The suggested next step is: {plain_treatment}.{vision_note} "
            f"If symptoms suddenly worsen, seek care immediately rather than waiting for follow-up."
        )

        recommendations.append({
            "type": "patient_explanation",
            "text": explanation,
            "confidence": 0.75,
            "priority": "LOW",
            "evidence": ["derived from consensus-moderator-approved findings"],
        })

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {"source_finding": top_finding, "source_treatment": treatment},
            "confidence": 0.75,
        }

    def _simplify(self, text: str) -> str:
        lowered = (text or "").lower()
        for jargon, plain in JARGON_SIMPLIFICATIONS.items():
            if jargon in lowered:
                return plain
        return text or "the situation is still being assessed"

    async def _get_key_outputs(self, context: AgentContext):
        finding = None
        treatment = None
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=200)
            for event in history:
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = event.payload.get("recommendation", {})
                    if rec.get("type") == "clinical_finding" and not finding:
                        finding = rec.get("text")
                    if rec.get("type") == "treatment_plan" and not treatment:
                        treatment = rec.get("text")
        except Exception as e:
            self.logger.warning(f"Could not read recommendation history: {e}")
        return finding, treatment
