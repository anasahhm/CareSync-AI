"""
Evidence Agent

Collects the evidence strings attached to every recommendation published so
far, ranks them by how many independent agents cite similar evidence, and
flags recommendations that carry no supporting evidence at all (which the
Hallucination Detection Agent downstream will weight heavily).
"""
import logging
from collections import Counter
from typing import Dict, Any, List

from app.agents import BaseAgent, AgentContext
from app.communication import EventType

logger = logging.getLogger(__name__)


class EvidenceAgent(BaseAgent):
    AGENT_TYPE = "EVIDENCE"
    AGENT_DESCRIPTION = "Collects and ranks evidence backing recommendations published so far"
    DEPENDENCIES = ["DIAGNOSTIC"]
    TIMEOUT_SECONDS = 12

    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        recommendations = []
        escalations = []

        recs_seen, unsupported = await self._collect_recommendations(context)

        backfilled = 0
        still_unsupported = []
        if self.rag and unsupported:
            for rec in unsupported[:5]:  # cap RAG calls per run
                claim_text = rec.get("text", "")
                if not claim_text:
                    still_unsupported.append(rec)
                    continue
                bundle = await self.rag.evidence_retriever.find_evidence(claim_text, top_k=2)
                if bundle.get("has_evidence"):
                    backfilled += 1
                else:
                    still_unsupported.append(rec)
        else:
            still_unsupported = unsupported

        evidence_terms = Counter()
        for rec in recs_seen:
            for ev in rec.get("evidence", []):
                evidence_terms[ev] += 1

        corroborated = [term for term, count in evidence_terms.items() if count > 1]

        if corroborated:
            recommendations.append({
                "type": "evidence_summary",
                "text": f"{len(corroborated)} evidence item(s) corroborated by multiple agents",
                "confidence": 0.8,
                "priority": "LOW",
                "evidence": corroborated[:10],
            })

        if backfilled:
            recommendations.append({
                "type": "evidence_backfill",
                "text": f"RAG located supporting evidence for {backfilled} previously unsupported claim(s)",
                "confidence": 0.7,
                "priority": "LOW",
                "evidence": [f"rag_backend={self.rag.retrieval_engine.vector_store.backend}"] if self.rag else [],
            })

        if still_unsupported:
            escalations.append({
                "level": "MEDIUM",
                "reason": f"{len(still_unsupported)} recommendation(s) have no supporting evidence even after RAG lookup",
                "type": "evidence_gap",
                "action": "Flag for Hallucination Detection and Quality Assurance review",
            })

        confidence = 0.75 if not still_unsupported else max(0.3, 0.75 - 0.1 * len(still_unsupported))

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": {
                "total_recommendations_reviewed": len(recs_seen),
                "unsupported_count": len(still_unsupported),
                "backfilled_count": backfilled,
                "corroborated_evidence_count": len(corroborated),
            },
            "confidence": confidence,
        }

    async def _collect_recommendations(self, context: AgentContext) -> (List[Dict], List[Dict]):
        recs: List[Dict[str, Any]] = []
        unsupported: List[Dict[str, Any]] = []
        try:
            history = await self.communication.get_event_history(context.consultation_id, limit=100)
            for event in history:
                if event.event_type == EventType.RECOMMENDATION_AVAILABLE:
                    rec = event.payload.get("recommendation", {})
                    recs.append(rec)
                    if not rec.get("evidence"):
                        unsupported.append(rec)
        except Exception as e:
            self.logger.warning(f"Could not read recommendation history: {e}")
        return recs, unsupported
