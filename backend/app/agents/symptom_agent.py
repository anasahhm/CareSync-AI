"""
Symptom Agent

Extracts and structures symptoms from the chief complaint, doctor notes, and
gesture/annotation events into a normalized symptom list consumed by the
Diagnostic Agent downstream.
"""
import logging
import re
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)

SYMPTOM_LEXICON = {
    "pain": ["pain", "ache", "sore", "hurts", "hurting"],
    "fever": ["fever", "temperature", "hot", "chills"],
    "respiratory": ["cough", "shortness of breath", "wheezing", "breathless"],
    "gastrointestinal": ["nausea", "vomiting", "diarrhea", "abdominal", "stomach"],
    "neurological": ["dizziness", "headache", "confusion", "numbness", "tingling"],
    "cardiac": ["chest pain", "palpitations", "irregular heartbeat"],
    "dermatological": ["rash", "swelling", "redness", "itching"],
    "musculoskeletal": ["stiffness", "weakness", "joint pain", "muscle"],
}


class SymptomAgent(BaseAgent):
    AGENT_TYPE = "SYMPTOM"
    AGENT_DESCRIPTION = "Extracts and structures symptoms from complaint, notes, and annotations"
    DEPENDENCIES = []
    TIMEOUT_SECONDS = 10

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        text = f"{context.chief_complaint or ''} {context.doctor_notes or ''}".lower()

        detected: List[Dict[str, Any]] = []
        for category, keywords in SYMPTOM_LEXICON.items():
            matches = [kw for kw in keywords if kw in text]
            if matches:
                detected.append({"category": category, "matched_terms": matches})

        # Fold in annotation/gesture derived symptom markers (e.g. body-area taps)
        for annotation in (context.annotations or []):
            label = str(annotation.get("label") or annotation.get("type") or "").lower()
            if label and label not in [d["category"] for d in detected]:
                detected.append({"category": "annotated_area", "matched_terms": [label]})

        vision_summary = await self._get_vision_summary(context)
        if vision_summary and vision_summary.get("pain_score", 0) > 0.4:
            detected.append({
                "category": "vision_detected_pain",
                "matched_terms": [f"body_part={vision_summary.get('body_part')}", f"pain_score={vision_summary.get('pain_score')}"],
            })

        duration_match = re.search(r"(\d+)\s*(day|days|week|weeks|month|months)", text)
        duration = duration_match.group(0) if duration_match else None

        confidence = 0.85 if detected else 0.4

        if detected:
            categories = ", ".join(sorted({d["category"] for d in detected}))
            recommendations.append({
                "type": "symptom_profile",
                "text": f"Structured symptom categories identified: {categories}",
                "confidence": confidence,
                "priority": "MEDIUM",
                "evidence": [f"{d['category']}: {', '.join(d['matched_terms'])}" for d in detected],
            })
        else:
            escalations.append({
                "level": "LOW",
                "reason": "No structured symptoms could be extracted from available text",
                "type": "data_quality",
                "action": "Request clarifying symptom description from patient/doctor",
            })

        if any(d["category"] == "cardiac" for d in detected) or any(d["category"] == "respiratory" for d in detected):
            escalations.append({
                "level": "HIGH",
                "reason": "Cardiac or respiratory symptom keywords detected",
                "type": "clinical_flag",
                "action": "Prioritize diagnostic review of cardiopulmonary symptoms",
            })

        if vision_summary and vision_summary.get("distress_flags"):
            escalations.append({
                "level": "MEDIUM",
                "reason": f"Vision pipeline detected distress signals: {', '.join(vision_summary['distress_flags'])}",
                "type": "vision_flag",
                "action": "Correlate visual distress signals with reported symptoms",
            })

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {
                "symptom_categories": [d["category"] for d in detected],
                "duration_mentioned": duration,
            },
            "confidence": confidence,
        }

    async def _get_vision_summary(self, context: AgentContext):
        if not self.vision:
            return None
        try:
            obs = self.vision.get_latest_observation(context.consultation_id)
            return obs.get("summary") if obs else None
        except Exception as e:
            self.logger.warning(f"Could not read vision observation: {e}")
            return None
