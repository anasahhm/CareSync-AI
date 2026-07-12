"""
Diagnostic Agent

Builds a ranked differential diagnosis from the Symptom Agent's structured
output and the Clinical Review Agent's findings. Downstream of both.
"""
import logging
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)

# category -> plausible differentials, ordered roughly by prevalence
DIFFERENTIAL_MAP = {
    "cardiac": [("Musculoskeletal chest wall pain", 0.4), ("Acute coronary syndrome", 0.3), ("Anxiety/panic-related chest pain", 0.3)],
    "respiratory": [("Viral upper respiratory infection", 0.45), ("Asthma exacerbation", 0.3), ("Pneumonia", 0.25)],
    "gastrointestinal": [("Viral gastroenteritis", 0.4), ("Gastritis", 0.3), ("Appendicitis (rule-out)", 0.3)],
    "neurological": [("Tension headache", 0.4), ("Migraine", 0.35), ("Vestibular disorder", 0.25)],
    "dermatological": [("Contact dermatitis", 0.45), ("Cellulitis (rule-out)", 0.3), ("Allergic reaction", 0.25)],
    "musculoskeletal": [("Muscle strain", 0.5), ("Joint inflammation", 0.3), ("Overuse injury", 0.2)],
    "fever": [("Viral syndrome", 0.5), ("Bacterial infection (rule-out)", 0.3), ("Inflammatory response", 0.2)],
    "pain": [("Localized soft-tissue injury", 0.4), ("Referred pain", 0.3), ("Nerve irritation", 0.3)],
    "vision_detected_pain": [("Localized pain confirmed by visual/behavioral signal", 0.35), ("Guarding-related musculoskeletal cause", 0.25)],
}


class DiagnosticAgent(BaseAgent):
    AGENT_TYPE = "DIAGNOSTIC"
    AGENT_DESCRIPTION = "Builds ranked differential diagnosis from symptom and clinical review findings"
    DEPENDENCIES = ["SYMPTOM", "CLINICAL_REVIEW"]
    TIMEOUT_SECONDS = 12

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        # Pull the symptom categories the Symptom Agent published via events,
        # falling back to a lightweight re-scan of the complaint if unavailable.
        categories = await self._get_symptom_categories(context)

        differential: List[Dict[str, Any]] = []
        for category in categories:
            for label, base_confidence in DIFFERENTIAL_MAP.get(category, []):
                differential.append({"diagnosis": label, "category": category, "confidence": base_confidence})

        if not differential:
            differential.append({"diagnosis": "Non-specific presentation - insufficient data", "category": "general", "confidence": 0.2})

        # Aggregate duplicate diagnoses that appear from multiple categories
        merged: Dict[str, Dict[str, Any]] = {}
        for item in differential:
            key = item["diagnosis"]
            if key in merged:
                merged[key]["confidence"] = min(0.95, merged[key]["confidence"] + item["confidence"] * 0.2)
                merged[key]["categories"].add(item["category"])
            else:
                merged[key] = {"confidence": item["confidence"], "categories": {item["category"]}}

        ranked = sorted(merged.items(), key=lambda kv: kv[1]["confidence"], reverse=True)

        overall_confidence = ranked[0][1]["confidence"] if ranked else 0.2

        for rank, (diagnosis, data) in enumerate(ranked[:5]):
            recommendations.append({
                "type": "clinical_finding" if rank == 0 else "differential_diagnosis",
                "text": diagnosis,
                "confidence": round(data["confidence"], 2),
                "priority": "HIGH" if rank == 0 and data["confidence"] >= 0.5 else "MEDIUM",
                "evidence": [f"category:{c}" for c in sorted(data["categories"])],
            })

        if overall_confidence < 0.35:
            escalations.append({
                "level": "MEDIUM",
                "reason": "Low-confidence differential diagnosis",
                "type": "diagnostic_uncertainty",
                "action": "Recommend additional history-taking or diagnostic testing before treatment planning",
            })

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {"differential_count": len(ranked), "top_diagnosis": ranked[0][0] if ranked else None},
            "confidence": overall_confidence,
        }

    async def _get_symptom_categories(self, context: AgentContext) -> List[str]:
        categories: List[str] = []
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=50)
            for event in history:
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = event.payload.get("recommendation", {})
                    if rec.get("type") == "symptom_profile":
                        for evidence_line in rec.get("evidence", []):
                            cat = evidence_line.split(":", 1)[0].strip()
                            if cat:
                                categories.append(cat)
        except Exception as e:
            self.logger.warning(f"Could not read symptom history, falling back to text scan: {e}")

        if not categories:
            text = f"{context.chief_complaint or ''}".lower()
            for category, keywords in {
                "cardiac": ["chest pain", "palpitations"],
                "respiratory": ["cough", "breath"],
                "gastrointestinal": ["nausea", "stomach", "vomit"],
                "neurological": ["headache", "dizziness"],
                "fever": ["fever", "temperature"],
                "pain": ["pain", "ache"],
            }.items():
                if any(kw in text for kw in keywords):
                    categories.append(category)

        return list(dict.fromkeys(categories)) or ["general"]
