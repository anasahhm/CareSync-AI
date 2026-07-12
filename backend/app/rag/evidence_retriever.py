"""
Evidence Retriever

Higher-level convenience wrapper the agents call: given a clinical claim
(e.g. a diagnosis or treatment text), pulls the best supporting evidence
from both the local guideline corpus and PubMed, merges them, and returns
citation-ready results. This is what EvidenceAgent and MedicalResearchAgent
call instead of talking to GuidelineRetriever/PubMedRetriever directly.
"""
import logging
from typing import List, Dict, Any

from app.rag.guideline_retriever import GuidelineRetriever
from app.rag.pubmed_retriever import PubMedRetriever
from app.rag.citation_engine import CitationEngine

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    def __init__(self, retrieval_engine, enable_pubmed: bool = True):
        self.guideline_retriever = GuidelineRetriever(retrieval_engine)
        self.pubmed_retriever = PubMedRetriever() if enable_pubmed else None

    async def find_evidence(self, claim: str, top_k: int = 3) -> Dict[str, Any]:
        guideline_hits = await self.guideline_retriever.retrieve(claim, top_k=top_k)

        pubmed_hits: List[Dict[str, Any]] = []
        if self.pubmed_retriever:
            pubmed_hits = await self.pubmed_retriever.search(claim, max_results=top_k)

        all_hits = guideline_hits + pubmed_hits
        citations = CitationEngine.format_all(all_hits)

        return {
            "claim": claim,
            "guideline_hits": guideline_hits,
            "pubmed_hits": pubmed_hits,
            "citations": citations,
            "has_evidence": bool(all_hits),
        }
