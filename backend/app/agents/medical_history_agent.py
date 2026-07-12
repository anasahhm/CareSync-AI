"""
Medical History Agent

Analyzes patient medical history and contextualizes current presentation.
Depends on Clinical Review Agent for symptom context.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class MedicalHistoryAgent(BaseAgent):
    AGENT_TYPE = "MEDICAL_HISTORY"
    AGENT_DESCRIPTION = "Analyzes patient medical history and contextualizes findings"
    DEPENDENCIES = ["CLINICAL_REVIEW"]
    TIMEOUT_SECONDS = 15
    
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze medical history and context"""
        
        recommendations = []
        escalations = []
        confidence = 0.75
        metadata = {}
        
        medical_history = context.medical_history or {}
        medications = context.patient_current_medications or []
        allergies = context.patient_allergies or []
        age = context.patient_age
        
        # History pattern analysis
        history_conditions = list(medical_history.keys()) if isinstance(medical_history, dict) else []
        
        if not history_conditions:
            recommendations.append({
                "type": "history_status",
                "text": "No significant medical history reported. Baseline presentation expected.",
                "confidence": 0.85,
                "priority": "LOW",
                "evidence": ["Empty medical history"]
            })
        else:
            recommendations.append({
                "type": "history_context",
                "text": f"Patient has medical history including: {', '.join(history_conditions)}",
                "confidence": 0.9,
                "priority": "MEDIUM",
                "evidence": ["Medical history documented"]
            })
        
        # Age-based risk assessment
        if age:
            if age < 18:
                recommendations.append({
                    "type": "age_factor",
                    "text": "Pediatric patient. Consider age-appropriate treatment options.",
                    "confidence": 0.9,
                    "priority": "HIGH",
                    "evidence": [f"Patient age: {age}"]
                })
                escalations.append({
                    "level": "MEDIUM",
                    "reason": "Pediatric patient requires special considerations",
                    "type": "pediatric_care",
                    "action": "Use pediatric dosing and monitoring protocols"
                })
            
            elif age > 65:
                recommendations.append({
                    "type": "age_factor",
                    "text": "Geriatric patient. Consider age-related physiological changes and polypharmacy.",
                    "confidence": 0.9,
                    "priority": "HIGH",
                    "evidence": [f"Patient age: {age}"]
                })
                escalations.append({
                    "level": "MEDIUM",
                    "reason": "Geriatric patient with increased risk factors",
                    "type": "geriatric_care",
                    "action": "Monitor for medication interactions and fall risk"
                })
        
        # Medication interaction analysis (simplified)
        if medications:
            recommendations.append({
                "type": "medication_review",
                "text": f"Patient currently taking: {', '.join(medications[:3])}{'...' if len(medications) > 3 else ''}",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Current medications documented"]
            })
            
            # Check for common interactions
            high_risk_combos = [
                ("warfarin", "aspirin"),
                ("metformin", "iodinated contrast"),
                ("lisinopril", "potassium supplements")
            ]
            
            med_lower = [m.lower() for m in medications]
            for drug1, drug2 in high_risk_combos:
                if drug1 in med_lower and drug2 in med_lower:
                    recommendations.append({
                        "type": "drug_interaction",
                        "text": f"Potential interaction between {drug1} and {drug2}. Monitor closely.",
                        "confidence": 0.85,
                        "priority": "CRITICAL",
                        "evidence": ["Known drug interaction"]
                    })
                    escalations.append({
                        "level": "HIGH",
                        "reason": "Serious drug interaction identified",
                        "type": "pharmacological_conflict",
                        "action": "Review and adjust medications if possible"
                    })
        
        # Chronic disease pattern matching
        chronic_conditions = ["diabetes", "hypertension", "asthma", "copd", "heart disease"]
        present_conditions = [
            c for c in chronic_conditions
            if c.lower() in str(medical_history).lower()
        ]
        
        if present_conditions:
            recommendations.append({
                "type": "chronic_disease",
                "text": f"Chronic conditions noted: {', '.join(present_conditions)}. Baseline management needed.",
                "confidence": 0.85,
                "priority": "HIGH",
                "evidence": ["Chronic disease history documented"]
            })
            
            escalations.append({
                "level": "MEDIUM",
                "reason": "Patient with chronic diseases requires ongoing management",
                "type": "chronic_disease_management",
                "action": "Monitor disease control markers and adjust treatment as needed"
            })
        
        # Recent surgery or hospitalization assessment
        recent_events_keywords = ["surgery", "hospitalization", "emergency", "admitted"]
        if any(keyword in str(medical_history).lower() for keyword in recent_events_keywords):
            recommendations.append({
                "type": "recent_event",
                "text": "Recent surgery or hospitalization documented. Monitor for post-operative complications.",
                "confidence": 0.8,
                "priority": "HIGH",
                "evidence": ["Recent medical event in history"]
            })
        
        # Allergy categorization
        if allergies:
            # Separate by type
            drug_allergies = [a for a in allergies if any(x in a.lower() for x in ["penicillin", "aspirin", "sulfa", "ibuprofen", "acetaminophen", "lisinopril", "metformin"])]
            food_allergies = [a for a in allergies if any(x in a.lower() for x in ["peanut", "shellfish", "milk", "egg", "wheat", "soy"])]
            
            if drug_allergies:
                recommendations.append({
                    "type": "drug_allergy",
                    "text": f"Drug allergies: {', '.join(drug_allergies)}. Avoid these medications.",
                    "confidence": 0.95,
                    "priority": "CRITICAL",
                    "evidence": ["Drug allergies documented"]
                })
                escalations.append({
                    "level": "CRITICAL",
                    "reason": "Drug allergy documented",
                    "type": "medication_safety",
                    "action": "Ensure alternative medications do not cross-react"
                })
            
            if food_allergies:
                recommendations.append({
                    "type": "food_allergy",
                    "text": f"Food allergies: {', '.join(food_allergies)}. Consider in dietary recommendations.",
                    "confidence": 0.85,
                    "priority": "MEDIUM",
                    "evidence": ["Food allergies documented"]
                })
        
        metadata = {
            "history_analyzed": len(history_conditions) > 0,
            "condition_count": len(history_conditions),
            "medication_count": len(medications),
            "allergy_count": len(allergies),
            "chronic_disease_count": len(present_conditions)
        }
        
        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": metadata,
            "confidence": confidence
        }