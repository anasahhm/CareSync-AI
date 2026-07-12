"""
Citation Engine

Formats retrieval hits (guideline snippets, PubMed summaries, or any other
retrieved evidence) into consistent, human-readable citation strings, and
de-duplicates citations across a single agent's output so a report doesn't
show the same source three times.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CitationEngine:
    @staticmethod
    def format_citation(hit: Dict[str, Any]) -> str:
        if hit.get("citation"):
            return hit["citation"]
        source = hit.get("source", "unknown source")
        topic = hit.get("topic")
        if topic:
            return f"{source} - {topic}"
        return source

    @staticmethod
    def format_all(hits: List[Dict[str, Any]]) -> List[str]:
        seen = set()
        citations = []
        for hit in hits:
            citation = CitationEngine.format_citation(hit)
            if citation not in seen:
                seen.add(citation)
                citations.append(citation)
        return citations

    @staticmethod
    def attach_citations_to_recommendation(recommendation: Dict[str, Any], hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        citations = CitationEngine.format_all(hits)
        evidence = list(recommendation.get("evidence", []))
        for c in citations:
            if c not in evidence:
                evidence.append(c)
        return {**recommendation, "evidence": evidence, "citations": citations}
