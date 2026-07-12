"""
Clinical Review Agent

Analyzes clinical symptoms, physical findings, and medical presentation.
No dependencies - runs immediately.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class ClinicalReviewAgent(BaseAgent):
    AGENT_TYPE = "CLINICAL_REVIEW"
    AGENT_DESCRIPTION = "Analyzes symptoms and clinical presentation"
    DEPENDENCIES = []  # No dependencies
    TIMEOUT_SECONDS = 15
    
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze clinical symptoms and presentation"""
        
        recommendations = []
        escalations = []
        confidence = 0.0
        metadata = {}
        
        # Rule-based symptom analysis (no LLM needed for hackathon)
        chief_complaint = context.chief_complaint or ""
        annotations_count = len(context.annotations)
        gesture_events_count = len(context.gesture_events)
        
        # Symptom classification
        if "shoulder" in chief_complaint.lower():
            recommendations.append({
                "type": "clinical_finding",
                "text": "Shoulder pain identified. Consider rotator cuff, impingement, or strain.",
                "confidence": 0.85,
                "priority": "HIGH",
                "evidence": ["Chief complaint mentions shoulder", f"{annotations_count} annotated areas"]
            })
            confidence = 0.85
            metadata["primary_condition"] = "Shoulder_Problem"
        
        elif "back" in chief_complaint.lower():
            recommendations.append({
                "type": "clinical_finding",
                "text": "Back pain identified. Consider muscle strain, disc issue, or structural problem.",
                "confidence": 0.82,
                "priority": "HIGH",
                "evidence": ["Chief complaint mentions back"]
            })
            confidence = 0.82
            metadata["primary_condition"] = "Back_Problem"
        
        elif "head" in chief_complaint.lower() or "headache" in chief_complaint.lower():
            recommendations.append({
                "type": "clinical_finding",
                "text": "Headache reported. Consider tension, migraine, or systemic cause.",
                "confidence": 0.78,
                "priority": "MEDIUM",
                "evidence": ["Chief complaint mentions headache"]
            })
            confidence = 0.78
            metadata["primary_condition"] = "Headache"
            
            # Escalate severe headaches
            escalations.append({
                "level": "MEDIUM",
                "reason": "Headache with neurological assessment needed",
                "type": "neuro_evaluation",
                "action": "Consider neurological exam if accompanied by other symptoms"
            })
        
        else:
            recommendations.append({
                "type": "clinical_finding",
                "text": f"Chief complaint: {chief_complaint}. Detailed examination recommended.",
                "confidence": 0.6,
                "priority": "MEDIUM",
                "evidence": ["Chief complaint provided"]
            })
            confidence = 0.6
        
        # Assess based on annotations (areas marked by doctor)
        if annotations_count > 3:
            recommendations.append({
                "type": "finding_severity",
                "text": f"Multiple areas marked ({annotations_count}). Suggests widespread or complex presentation.",
                "confidence": 0.75,
                "priority": "HIGH",
                "evidence": [f"{annotations_count} areas annotated during exam"]
            })
        
        # Assess gesture signals
        if gesture_events_count > 10:
            recommendations.append({
                "type": "patient_engagement",
                "text": "High gesture activity. Patient appears engaged and responsive.",
                "confidence": 0.8,
                "priority": "LOW",
                "evidence": [f"{gesture_events_count} gesture events captured"]
            })
        
        # Check for red flags in medical history
        medical_history = context.medical_history or {}
        allergies = context.patient_allergies or []
        medications = context.patient_current_medications or []
        
        # Red flag check: previous serious conditions
        serious_conditions = ["cancer", "stroke", "heart", "diabetes"]
        has_serious_history = any(
            cond.lower() in str(medical_history).lower()
            for cond in serious_conditions
        )
        
        if has_serious_history:
            recommendations.append({
                "type": "clinical_flag",
                "text": "Significant medical history noted. Consider chronic disease impact.",
                "confidence": 0.8,
                "priority": "HIGH",
                "evidence": ["Medical history indicates serious previous conditions"]
            })
            escalations.append({
                "level": "HIGH",
                "reason": "Patient has significant medical history",
                "type": "chronic_disease_consideration",
                "action": "Consider interactions and comorbidities in treatment planning"
            })
        
        # Check allergies
        if allergies and "aspirin" in str(allergies).lower():
            recommendations.append({
                "type": "safety_flag",
                "text": "Aspirin allergy noted. Avoid NSAIDs, use alternative analgesics.",
                "confidence": 0.95,
                "priority": "CRITICAL",
                "evidence": ["Aspirin allergy documented"]
            })
        
        if allergies:
            recommendations.append({
                "type": "allergy_consideration",
                "text": f"Patient has documented allergies: {', '.join(allergies)}",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Allergies documented in patient profile"]
            })

        # Polypharmacy check: 5+ concurrent medications raises interaction risk
        if len(medications) >= 5:
            recommendations.append({
                "type": "polypharmacy_flag",
                "text": f"Patient is on {len(medications)} concurrent medications; review for interaction risk",
                "confidence": 0.75,
                "priority": "MEDIUM",
                "evidence": [f"medications={', '.join(medications)}"]
            })
            escalations.append({
                "level": "MEDIUM",
                "reason": f"Polypharmacy detected ({len(medications)} medications)",
                "type": "medication_interaction_risk",
                "action": "Cross-check new treatment plan against existing medication list before finalizing"
            })

        # Initial severity assessment
        if "severe" in chief_complaint.lower() or "emergency" in chief_complaint.lower():
            escalations.append({
                "level": "HIGH",
                "reason": "Severe symptoms reported",
                "type": "severity_assessment",
                "action": "Urgent evaluation and possible emergency intervention"
            })

        # Vision integration: fold in the fused pain/distress observation
        # (available: False on every field if MediaPipe/no camera - safe to
        # check unconditionally)
        if self.vision:
            try:
                observation = self.vision.get_latest_observation(context.consultation_id)
                if observation:
                    vsummary = observation.get("summary", {})
                    if vsummary.get("pain_score", 0) > 0.5:
                        recommendations.append({
                            "type": "clinical_finding",
                            "text": f"Visual/behavioral signals indicate pain (score={vsummary['pain_score']}, area={vsummary.get('body_part') or 'unspecified'})",
                            "confidence": observation.get("summary", {}).get("confidence", 0.5),
                            "priority": "MEDIUM",
                            "evidence": [f"vision_signals={vsummary.get('distress_flags')}"],
                        })
                    if vsummary.get("distress_flags"):
                        escalations.append({
                            "level": "MEDIUM",
                            "reason": f"Vision pipeline flagged distress indicators: {', '.join(vsummary['distress_flags'])}",
                            "type": "vision_flag",
                            "action": "Correlate with reported chief complaint before finalizing severity",
                        })
                    metadata["vision_summary"] = vsummary
            except Exception as e:
                logger.warning(f"ClinicalReviewAgent: could not read vision observation (non-fatal): {e}")

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": metadata,
            "confidence": confidence
        }