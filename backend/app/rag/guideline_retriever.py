"""
Guideline Retriever

Seeds and queries a small curated corpus of WHO/CDC-style clinical
guideline snippets. This is the RAG-backed replacement for the hardcoded
LOCAL_GUIDELINES dict that used to live directly inside
MedicalResearchAgent - the corpus content is the same starting data, but it
now goes through real embedding + vector search instead of a keyword
substring match, and every hit carries a citation.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Curated seed corpus. In production this would be loaded from indexed
# WHO/CDC/PubMed documents; kept small and explicit here so the system is
# fully offline-runnable without any external fetch at startup.
GUIDELINE_CORPUS = [
    {
        "id": "who-chest-pain-01",
        "source": "WHO Emergency Care Guidelines (adapted)",
        "topic": "chest wall pain",
        "text": "Reassess for red-flag cardiac features (radiating pain, diaphoresis, dyspnea) before attributing chest pain to a musculoskeletal cause.",
    },
    {
        "id": "cdc-acs-01",
        "source": "CDC Cardiovascular Guidance (adapted)",
        "topic": "acute coronary syndrome",
        "text": "Obtain a 12-lead ECG and troponin promptly for suspected acute coronary syndrome; do not delay definitive workup for outpatient scheduling.",
    },
    {
        "id": "who-resp-01",
        "source": "WHO Respiratory Illness Guidelines (adapted)",
        "topic": "respiratory infection",
        "text": "Provide supportive care for viral upper respiratory infections; reserve antibiotics for confirmed or strongly suspected bacterial superinfection.",
    },
    {
        "id": "cdc-asthma-01",
        "source": "CDC Asthma Management Guidance (adapted)",
        "topic": "asthma",
        "text": "Assess peak expiratory flow and oxygen saturation; step up bronchodilator therapy according to exacerbation severity.",
    },
    {
        "id": "who-gastro-01",
        "source": "WHO Diarrhoeal Disease Guidelines (adapted)",
        "topic": "gastroenteritis",
        "text": "Prioritize oral rehydration therapy for viral gastroenteritis; escalate to further workup if signs of dehydration or peritoneal irritation appear.",
    },
    {
        "id": "who-headache-01",
        "source": "WHO Headache Disorders Guidelines (adapted)",
        "topic": "migraine",
        "text": "Screen for red-flag headache features (thunderclap onset, focal neurological deficit, fever with neck stiffness) before treating as primary migraine.",
    },
    {
        "id": "cdc-cellulitis-01",
        "source": "CDC Skin Infection Guidance (adapted)",
        "topic": "cellulitis",
        "text": "Mark the borders of cellulitis, begin empiric antibiotics covering common skin flora, and reassess for improvement within 48 to 72 hours.",
    },
    {
        "id": "who-msk-01",
        "source": "WHO Musculoskeletal Injury Guidelines (adapted)",
        "topic": "muscle strain",
        "text": "Manage uncomplicated muscle strain conservatively with rest, ice, and NSAIDs as tolerated; escalate promptly if a neurological deficit is present.",
    },
]


class GuidelineRetriever:
    def __init__(self, retrieval_engine):
        self.retrieval_engine = retrieval_engine
        self._seeded = False

    async def seed(self) -> int:
        if self._seeded:
            return 0
        count = 0
        for entry in GUIDELINE_CORPUS:
            await self.retrieval_engine.index_document(
                text=entry["text"],
                metadata={"id": entry["id"], "source": entry["source"], "topic": entry["topic"], "kind": "guideline"},
            )
            count += 1
        self._seeded = True
        logger.info(f"GuidelineRetriever seeded {count} guideline documents")
        return count

    async def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        await self.seed()
        results = await self.retrieval_engine.retrieve(query, top_k=top_k, kind_filter="guideline")
        return results
