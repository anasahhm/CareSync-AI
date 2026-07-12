"""
Consensus Engine

Real consensus computation extracted from ConsultationOrchestrator so it can
be unit-tested and reused independently. Incorporates:
  - weighted voting across all completed agents (original consensus logic)
  - a confidence penalty when Hallucination Detection or QA agents flagged
    the run
  - deference to the Consensus Moderator agent's rulings when present, so a
    moderator decision on a conflicting category outranks a simple
    highest-confidence pick
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

RISK_LEVEL_WEIGHTS = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8, "CRITICAL": 1.0}


class ConsensusEngine:
    def __init__(self, total_agents: int):
        self.total_agents = total_agents

    def build_consensus(
        self,
        agent_outputs: Dict[str, Dict[str, Any]],
        moderator_rulings: List[Dict[str, Any]] = None,
        vision_observation: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        moderator_rulings = moderator_rulings or []

        completed_agents = {
            agent_type: output for agent_type, output in agent_outputs.items()
            if output.get("status") == "COMPLETED"
        }
        completed_count = len(completed_agents)

        if completed_count == 0:
            return {
                "total_agents_executed": 0,
                "primary_diagnosis": None,
                "consensus_score": 0.0,
                "overall_risk_score": 1.0,
                "final_recommendations": [],
                "requires_doctor_review": True,
            }

        all_recommendations: List[Dict[str, Any]] = []
        recommendation_counts: Dict[str, int] = {}
        risk_factors: List[Dict[str, Any]] = []

        for agent_type, output in completed_agents.items():
            confidence = output.get("confidence", 0.7)
            for rec in output.get("recommendations", []):
                weighted_confidence = rec.get("confidence", 0.8) * confidence
                all_recommendations.append({
                    **rec,
                    "source_agent": agent_type,
                    "weighted_confidence": weighted_confidence,
                })
                rec_type = rec.get("type", "general")
                recommendation_counts[rec_type] = recommendation_counts.get(rec_type, 0) + 1

            for escal in output.get("escalations", []):
                risk_factors.append({
                    "source_agent": agent_type,
                    "level": escal.get("level", "LOW"),
                    "reason": escal.get("reason"),
                })

        if vision_observation:
            summary = vision_observation.get("summary", {})
            vision_confidence = summary.get("confidence", 0.0)
            if summary.get("pain_score", 0) > 0:
                all_recommendations.append({
                    "type": "vision_finding",
                    "text": f"Visual/behavioral pain signal (score={summary['pain_score']}, area={summary.get('body_part') or 'unspecified'})",
                    "source_agent": "VISION",
                    "confidence": vision_confidence,
                    "weighted_confidence": summary["pain_score"] * max(vision_confidence, 0.3),
                    "evidence": [f"signals={summary.get('distress_flags')}"],
                })
            if summary.get("distress_flags"):
                risk_factors.append({
                    "source_agent": "VISION",
                    "level": "MEDIUM" if len(summary["distress_flags"]) < 2 else "HIGH",
                    "reason": f"Vision pipeline distress flags: {', '.join(summary['distress_flags'])}",
                })

        # Apply moderator rulings: boost the chosen claim, demote alternatives
        # in the same category so the final ranking reflects the moderator's
        # tie-break rather than a raw confidence race.
        ruling_by_type = {r["type"]: r for r in moderator_rulings}
        for rec in all_recommendations:
            ruling = ruling_by_type.get(rec.get("type"))
            if not ruling:
                continue
            if rec.get("text") == ruling.get("chosen"):
                rec["weighted_confidence"] = min(0.98, rec["weighted_confidence"] + 0.1)
                rec["moderator_endorsed"] = True
            else:
                rec["weighted_confidence"] = max(0.05, rec["weighted_confidence"] - 0.15)

        # Confidence penalty if hallucination/QA gates flagged the run
        hallucination_penalty = self._safety_gate_penalty(completed_agents)

        avg_confidence = 0.0
        if all_recommendations:
            total_confidence = sum(r.get("weighted_confidence", 0.7) for r in all_recommendations)
            avg_confidence = (total_confidence / len(all_recommendations)) * hallucination_penalty

        consensus_score = (completed_count / self.total_agents) * avg_confidence

        overall_risk_score = 0.1
        if risk_factors:
            total_risk = sum(RISK_LEVEL_WEIGHTS.get(f.get("level", "LOW"), 0.2) for f in risk_factors)
            overall_risk_score = min(1.0, total_risk / len(risk_factors))

        sorted_recommendations = sorted(
            all_recommendations, key=lambda x: x.get("weighted_confidence", 0), reverse=True
        )

        primary_diagnosis = next(
            (r.get("text") for r in sorted_recommendations if r.get("type") == "clinical_finding"), None
        )

        agent_agreement_counts = {
            rec_type: {"total_mentions": count, "agreement_level": min(1.0, count / completed_count)}
            for rec_type, count in recommendation_counts.items()
        }

        conflicts = []
        treatment_recs = [r for r in sorted_recommendations if r.get("type") == "treatment_plan"]
        if len(treatment_recs) > 1:
            texts = {r.get("text", "") for r in treatment_recs}
            if len(texts) > 1 and len(treatment_recs) > 2 and not any(r.get("moderator_endorsed") for r in treatment_recs):
                conflicts.append({
                    "type": "treatment_divergence",
                    "severity": "MEDIUM",
                    "description": "Multiple agents recommended different treatment approaches",
                })

        return {
            "total_agents_executed": completed_count,
            "total_agents_agreed": len(completed_agents),
            "primary_diagnosis": primary_diagnosis,
            "final_recommendations": sorted_recommendations[:10],
            "consensus_score": consensus_score,
            "overall_risk_score": overall_risk_score,
            "risk_factors": risk_factors,
            "agent_agreements": agent_agreement_counts,
            "conflicts": conflicts,
            "moderator_rulings_applied": len(moderator_rulings),
            "requires_doctor_review": overall_risk_score > 0.6 or len(conflicts) > 0 or hallucination_penalty < 0.9,
        }

    def _safety_gate_penalty(self, completed_agents: Dict[str, Dict[str, Any]]) -> float:
        """Reduce overall confidence if hallucination detection or QA flagged problems."""
        penalty = 1.0

        hallucination_output = completed_agents.get("HALLUCINATION_DETECTION")
        if hallucination_output:
            for rec in hallucination_output.get("recommendations", []):
                if rec.get("type") == "hallucination_review" and "flagged" in (rec.get("text") or "").lower():
                    penalty *= 0.85

        qa_output = completed_agents.get("QUALITY_ASSURANCE")
        if qa_output:
            for rec in qa_output.get("recommendations", []):
                if rec.get("type") == "qa_gate" and "FAILED" in (rec.get("text") or ""):
                    penalty *= 0.8

        return penalty
