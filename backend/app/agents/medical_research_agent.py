"""
Medical Research Agent

Surfaces relevant clinical-guideline context for the leading diagnosis.
Now backed by the real RAG layer (RetrievalEngine -> Qdrant/FAISS +
sentence-transformers, seeded from GuidelineRetriever's corpus) when a
RAGManager has been injected by AgentService; falls back to the original
lightweight local-dict lookup if RAG isn't wired up yet (e.g. in unit
tests that construct the agent directly), so behavior degrades gracefully
rather than breaking.
"""
import logging
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)

# Retained as the no-RAG fallback path only (previously the sole
# implementation) - see _lookup_guidelines_fallback.
LOCAL_GUIDELINES = {
    "chest wall pain": ["Reassess for red-flag cardiac features before attributing pain to musculoskeletal cause."],
    "acute coronary syndrome": ["Obtain ECG and troponin promptly; do not delay for outpatient workup if suspected."],
    "respiratory infection": ["Supportive care; antibiotics only if bacterial superinfection is suspected."],
    "asthma": ["Assess peak flow / SpO2; step up bronchodilator therapy per severity."],
    "gastroenteritis": ["Prioritize oral rehydration; escalate if signs of dehydration or peritoneal signs."],
    "migraine": ["First-line abortive therapy; screen for red-flag headache features (thunderclap, focal deficit)."],
    "cellulitis": ["Mark borders, start empiric antibiotics, reassess in 48-72h for improvement."],
    "muscle strain": ["Conservative management: rest, ice, NSAIDs as tolerated; escalate if neuro deficit."],
}


class MedicalResearchAgent(BaseAgent):
    AGENT_TYPE = "MEDICAL_RESEARCH"
    AGENT_DESCRIPTION = "Surfaces relevant clinical guideline context for the leading diagnosis via RAG"
    DEPENDENCIES = ["DIAGNOSTIC"]
    TIMEOUT_SECONDS = 15

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        top_diagnosis = await self._get_top_diagnosis(context)

        if self.rag:
            evidence_bundle = await self.rag.evidence_retriever.find_evidence(top_diagnosis, top_k=3)
            guideline_texts = [h.get("text") for h in evidence_bundle.get("guideline_hits", [])]
            citations = evidence_bundle.get("citations", [])
        else:
            guideline_texts = self._lookup_guidelines_fallback(top_diagnosis)
            citations = guideline_texts

        if guideline_texts:
            recommendations.append({
                "type": "guideline_reference",
                "text": f"Guideline context for '{top_diagnosis}': {guideline_texts[0]}",
                "confidence": 0.75,
                "priority": "MEDIUM",
                "evidence": citations,
            })
            confidence = 0.75
        else:
            escalations.append({
                "level": "LOW",
                "reason": f"No guideline evidence found for '{top_diagnosis}'",
                "type": "knowledge_gap",
                "action": "Consult external reference (UpToDate/WHO/CDC) manually",
            })
            confidence = 0.3

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {
                "queried_diagnosis": top_diagnosis,
                "guideline_hits": len(guideline_texts),
                "rag_backed": bool(self.rag),
            },
            "confidence": confidence,
        }

    def _lookup_guidelines_fallback(self, diagnosis: str) -> List[str]:
        if not diagnosis:
            return []
        diagnosis_lower = diagnosis.lower()
        for key, snippets in LOCAL_GUIDELINES.items():
            if key in diagnosis_lower:
                return snippets
        return []

    async def _get_top_diagnosis(self, context: AgentContext) -> str:
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=50)
            for event in reversed(history):
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = event.payload.get("recommendation", {})
                    if rec.get("type") == "clinical_finding":
                        return rec.get("text", "")
        except Exception as e:
            self.logger.warning(f"Could not read diagnostic history: {e}")
        return context.chief_complaint or ""
