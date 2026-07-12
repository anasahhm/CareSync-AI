"""
Recommendation Validator

Grounding check used by the Hallucination Detection Agent and Quality
Assurance Agent: given a recommendation's text and the evidence retrieved
for it, scores how well the claim is actually supported by that evidence
(term overlap - conservative and deterministic, not an LLM judge).
"""
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


class RecommendationValidator:
    @staticmethod
    def score_grounding(claim_text: str, evidence_texts: List[str]) -> float:
        if not evidence_texts:
            return 0.0
        claim_tokens = _tokenize(claim_text)
        if not claim_tokens:
            return 0.0

        best_overlap = 0.0
        for evidence in evidence_texts:
            evidence_tokens = _tokenize(evidence)
            if not evidence_tokens:
                continue
            overlap = len(claim_tokens & evidence_tokens) / len(claim_tokens)
            best_overlap = max(best_overlap, overlap)
        return round(min(1.0, best_overlap), 3)

    @staticmethod
    def validate(recommendation: Dict[str, Any], evidence_bundle: Dict[str, Any]) -> Dict[str, Any]:
        evidence_texts = [h.get("text", "") for h in evidence_bundle.get("guideline_hits", [])]
        evidence_texts += [h.get("title", "") for h in evidence_bundle.get("pubmed_hits", [])]

        grounding_score = RecommendationValidator.score_grounding(recommendation.get("text", ""), evidence_texts)

        return {
            **recommendation,
            "grounding_score": grounding_score,
            "well_grounded": grounding_score >= 0.15 or evidence_bundle.get("has_evidence", False),
        }
