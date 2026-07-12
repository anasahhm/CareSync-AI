"""
Report Aggregator

Builds the final structured report handed to /api/reports and the frontend
ReportViewer, combining the persisted AgentProcessingReport row with the raw
consensus/agent-output dict produced during this run. Kept separate from
ConsensusEngine because this is presentation/aggregation, not scoring.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class ReportAggregator:
    @staticmethod
    def build_report(
        consultation_id: str,
        processing_report: Any,
        agent_outputs: Dict[str, Dict[str, Any]],
        consensus: Dict[str, Any],
    ) -> Dict[str, Any]:
        recommendations = consensus.get("final_recommendations", [])
        sorted_recs = sorted(
            recommendations,
            key=lambda r: PRIORITY_ORDER.get(r.get("priority", "LOW"), 3),
        )

        patient_explanation = next(
            (r.get("text") for r in recommendations if r.get("type") == "patient_explanation"),
            None,
        )

        escalation_summary = next(
            (r.get("text") for r in recommendations if r.get("type") == "final_escalation_summary"),
            None,
        )

        agent_status_summary = {
            agent_type: {
                "status": output.get("status"),
                "duration_ms": output.get("duration_ms"),
                "confidence": output.get("confidence"),
            }
            for agent_type, output in agent_outputs.items()
        }

        return {
            "consultation_id": consultation_id,
            "generated_at": getattr(processing_report, "completed_at", None),
            "processing_status": getattr(processing_report, "processing_status", consensus and "COMPLETED"),
            "duration_seconds": getattr(processing_report, "total_duration_seconds", None),
            "primary_diagnosis": consensus.get("primary_diagnosis"),
            "consensus_score": consensus.get("consensus_score", 0.0),
            "overall_risk_score": consensus.get("overall_risk_score", 0.0),
            "requires_doctor_review": consensus.get("requires_doctor_review", True),
            "patient_explanation": patient_explanation,
            "escalation_summary": escalation_summary,
            "recommendations": sorted_recs,
            "conflicts": consensus.get("conflicts", []),
            "moderator_rulings_applied": consensus.get("moderator_rulings_applied", 0),
            "agent_status": agent_status_summary,
            "agents_executed": list(agent_outputs.keys()),
        }

    @staticmethod
    def to_markdown(report: Dict[str, Any]) -> str:
        lines = [
            f"# Consultation Report - {report['consultation_id']}",
            "",
            f"**Primary finding:** {report.get('primary_diagnosis') or 'Not determined'}",
            f"**Consensus score:** {report.get('consensus_score', 0):.2f}",
            f"**Overall risk score:** {report.get('overall_risk_score', 0):.2f}",
            f"**Requires doctor review:** {report.get('requires_doctor_review')}",
            "",
        ]
        if report.get("patient_explanation"):
            lines += ["## For the patient", report["patient_explanation"], ""]
        if report.get("escalation_summary"):
            lines += ["## Escalation summary", report["escalation_summary"], ""]

        lines.append("## Recommendations")
        for rec in report.get("recommendations", []):
            lines.append(f"- **[{rec.get('priority', 'LOW')}]** {rec.get('text')} (confidence: {rec.get('weighted_confidence', rec.get('confidence', 0)):.2f}, source: {rec.get('source_agent', 'unknown')})")

        return "\n".join(lines)
