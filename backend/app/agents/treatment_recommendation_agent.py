"""
Treatment Recommendation Agent

Generates evidence-based treatment recommendations considering medical history and allergies.
Depends on Clinical Review and Medical History agents.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class TreatmentRecommendationAgent(BaseAgent):
    AGENT_TYPE = "TREATMENT_RECOMMENDATION"
    AGENT_DESCRIPTION = "Generates evidence-based treatment recommendations"
    DEPENDENCIES = ["CLINICAL_REVIEW", "MEDICAL_HISTORY"]
    TIMEOUT_SECONDS = 20
    
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """Generate treatment recommendations"""
        
        recommendations = []
        escalations = []
        confidence = 0.8
        metadata = {}
        
        chief_complaint = (context.chief_complaint or "").lower()
        allergies = context.patient_allergies or []
        medications = context.patient_current_medications or []
        
        # Treatment pathways based on condition (simplified decision tree)
        
        # Shoulder pain treatment
        if "shoulder" in chief_complaint:
            recommendations.append({
                "type": "treatment_plan",
                "text": "First-line: Rest, ice, NSAIDs (if no contraindications), physical therapy",
                "confidence": 0.85,
                "priority": "HIGH",
                "evidence": ["Shoulder pain diagnosis"]
            })
            
            # Check for aspirin/NSAID allergy
            if "aspirin" in str(allergies).lower() or "nsaid" in str(allergies).lower():
                recommendations.append({
                    "type": "alternative_treatment",
                    "text": "NSAID contraindicated. Use acetaminophen and topical agents instead.",
                    "confidence": 0.9,
                    "priority": "CRITICAL",
                    "evidence": ["NSAID allergy documented"]
                })
            else:
                recommendations.append({
                    "type": "medication",
                    "text": "Consider: Ibuprofen 400-600mg TID, or Naproxen 220-440mg BID",
                    "confidence": 0.85,
                    "priority": "MEDIUM",
                    "evidence": ["Standard first-line therapy"]
                })
            
            recommendations.append({
                "type": "therapy",
                "text": "Physical therapy: ROM exercises, strengthening, manual therapy",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Evidence-based for shoulder pain"]
            })
            
            recommendations.append({
                "type": "follow_up",
                "text": "Follow up in 2 weeks. If no improvement, consider imaging (X-ray, MRI) or specialist referral.",
                "confidence": 0.85,
                "priority": "MEDIUM",
                "evidence": ["Standard follow-up protocol"]
            })
        
        # Back pain treatment
        elif "back" in chief_complaint:
            recommendations.append({
                "type": "treatment_plan",
                "text": "First-line: Rest, heat/ice, NSAIDs, core strengthening exercises",
                "confidence": 0.85,
                "priority": "HIGH",
                "evidence": ["Back pain diagnosis"]
            })
            
            if "aspirin" not in str(allergies).lower():
                recommendations.append({
                    "type": "medication",
                    "text": "Muscle relaxant: Consider cyclobenzaprine 5-10mg THS for acute muscle spasm",
                    "confidence": 0.8,
                    "priority": "MEDIUM",
                    "evidence": ["Appropriate for muscle-related back pain"]
                })
            
            recommendations.append({
                "type": "patient_education",
                "text": "Ergonomic assessment, proper lifting techniques, avoid prolonged sitting",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Prevention of recurrence critical"]
            })
        
        # Headache treatment
        elif "headache" in chief_complaint or "head" in chief_complaint:
            recommendations.append({
                "type": "treatment_plan",
                "text": "Assess type: tension vs migraine vs other. Tailor treatment accordingly.",
                "confidence": 0.8,
                "priority": "MEDIUM",
                "evidence": ["Headache requires differential diagnosis"]
            })
            
            recommendations.append({
                "type": "acute_therapy",
                "text": "Acute: Acetaminophen 650mg or Ibuprofen 400-600mg",
                "confidence": 0.85,
                "priority": "MEDIUM",
                "evidence": ["First-line OTC options"]
            })
            
            recommendations.append({
                "type": "preventive_therapy",
                "text": "If recurrent: Consider preventive therapy (beta-blocker, tricyclic antidepressant)",
                "confidence": 0.75,
                "priority": "MEDIUM",
                "evidence": ["For chronic/frequent headaches"]
            })
        
        # Generic recommendations for any condition
        recommendations.append({
            "type": "general_measures",
            "text": "Hydration, adequate sleep, stress management, lifestyle modifications",
            "confidence": 0.9,
            "priority": "MEDIUM",
            "evidence": ["Universal supportive measures"]
        })
        
        # Drug interaction check
        if medications:
            med_lower = [m.lower() for m in medications]
            
            # Warfarin interactions
            if any("warfarin" in m or "coumadin" in m for m in med_lower):
                recommendations.append({
                    "type": "interaction_warning",
                    "text": "Patient on warfarin - avoid NSAIDs. Use acetaminophen for pain.",
                    "confidence": 0.95,
                    "priority": "CRITICAL",
                    "evidence": ["Warfarin contraindication"]
                })
                escalations.append({
                    "level": "HIGH",
                    "reason": "Anticoagulation therapy requires special medication considerations",
                    "type": "anticoagulation_management",
                    "action": "Coordinate with prescribing physician"
                })
        
        # Renal/hepatic impairment considerations
        if "kidney disease" in str(context.medical_history).lower() or "liver disease" in str(context.medical_history).lower():
            recommendations.append({
                "type": "organ_function",
                "text": "Renal/hepatic impairment documented. Adjust medication dosing accordingly.",
                "confidence": 0.85,
                "priority": "CRITICAL",
                "evidence": ["Organ impairment in medical history"]
            })
        
        metadata = {
            "treatment_plan_generated": True,
            "contraindications_checked": True,
            "interactions_reviewed": len(medications) > 0,
            "condition_specific": True
        }

        if self.vision:
            try:
                observation = self.vision.get_latest_observation(context.consultation_id)
                if observation:
                    vsummary = observation.get("summary", {})
                    if vsummary.get("pain_score", 0) > 0.6:
                        recommendations.append({
                            "type": "treatment_plan",
                            "text": "Prioritize pain management given visually/behaviorally observed pain severity",
                            "confidence": 0.65,
                            "priority": "HIGH",
                            "evidence": [f"vision_pain_score={vsummary['pain_score']}"],
                        })
                    metadata["vision_pain_score"] = vsummary.get("pain_score")
            except Exception as e:
                logger.warning(f"TreatmentRecommendationAgent: could not read vision observation (non-fatal): {e}")

        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": metadata,
            "confidence": confidence
        }