"""
Triage & Escalation Agent

Determines patient urgency and escalation requirements based on clinical presentation.
Depends on Clinical Review Agent for symptom context.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class TriageEscalationAgent(BaseAgent):
    AGENT_TYPE = "TRIAGE_ESCALATION"
    AGENT_DESCRIPTION = "Determines patient urgency and escalation requirements"
    DEPENDENCIES = ["CLINICAL_REVIEW"]
    TIMEOUT_SECONDS = 10
    
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """Determine triage level and escalation requirements"""
        
        recommendations = []
        escalations = []
        confidence = 0.85
        metadata = {}
        
        chief_complaint = (context.chief_complaint or "").lower()
        annotations_count = len(context.annotations)
        
        # ESI-5 Triage Protocol (simplified)
        triage_level = 4  # Default: low urgency
        triage_reason = "Routine complaint, stable presentation"
        
        # Level 1: Immediate risk to life
        immediate_threats = ["unresponsive", "unconscious", "severe", "critical", "emergency"]
        if any(threat in chief_complaint for threat in immediate_threats):
            triage_level = 1
            triage_reason = "Immediate threat to life"
            escalations.append({
                "level": "CRITICAL",
                "reason": "ESI Level 1 - Immediate danger",
                "type": "emergency_activation",
                "action": "Activate emergency protocols, consider 911"
            })
        
        # Level 2: Emergent - situation may deteriorate
        emergent_symptoms = ["severe pain", "shortness of breath", "chest pain", "stroke symptoms", "head injury"]
        if any(symptom in chief_complaint for symptom in emergent_symptoms):
            triage_level = 2
            triage_reason = "Emergent condition, may deteriorate"
            escalations.append({
                "level": "CRITICAL",
                "reason": "ESI Level 2 - Emergent presentation",
                "type": "urgent_evaluation_required",
                "action": "Prioritize for immediate physician evaluation"
            })
        
        # Level 3: Urgent - requires treatment within 1 hour
        urgent_symptoms = ["moderate pain", "swelling", "infection signs", "fever"]
        if any(symptom in chief_complaint for symptom in urgent_symptoms):
            if triage_level > 3:
                triage_level = 3
                triage_reason = "Urgent - requires treatment within 1 hour"
        
        # Level 4: Semi-urgent - treatable within 2-3 hours
        if annotations_count >= 2:
            if triage_level > 4:
                triage_level = 4
                triage_reason = "Semi-urgent - multiple areas affected"
        
        # Generate triage recommendation
        recommendations.append({
            "type": "triage_level",
            "text": f"ESI Triage Level {triage_level}: {triage_reason}",
            "confidence": 0.9,
            "priority": "CRITICAL" if triage_level <= 2 else "HIGH" if triage_level == 3 else "MEDIUM",
            "evidence": ["Triage assessment completed"]
        })
        
        # Time-sensitive conditions requiring urgent action
        time_critical = ["stroke", "heart attack", "sepsis", "anaphylaxis"]
        if any(cond in chief_complaint for cond in time_critical):
            escalations.append({
                "level": "CRITICAL",
                "reason": "Time-critical condition - minutes matter",
                "type": "time_sensitive_emergency",
                "action": "Activate rapid response protocols"
            })
        
        # Escalation pathway recommendations
        if triage_level <= 2:
            recommendations.append({
                "type": "escalation_pathway",
                "text": "Route to Emergency Department for immediate evaluation.",
                "confidence": 0.95,
                "priority": "CRITICAL",
                "evidence": ["High acuity presentation"]
            })
        elif triage_level == 3:
            recommendations.append({
                "type": "escalation_pathway",
                "text": "Route to Urgent Care or ED depending on specific condition.",
                "confidence": 0.85,
                "priority": "HIGH",
                "evidence": ["Urgent condition identified"]
            })
        else:
            recommendations.append({
                "type": "escalation_pathway",
                "text": "Can be managed in primary care or telemedicine setting.",
                "confidence": 0.8,
                "priority": "MEDIUM",
                "evidence": ["Low acuity presentation"]
            })
        
        # Monitoring requirements based on triage
        if triage_level <= 3:
            recommendations.append({
                "type": "monitoring",
                "text": "Continuous vital sign monitoring required during triage.",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["High acuity level"]
            })
        
        # Red flags requiring immediate escalation
        red_flags = {
            "altered mental status": "CRITICAL",
            "respiratory distress": "CRITICAL",
            "uncontrolled bleeding": "CRITICAL",
            "severe allergic reaction": "CRITICAL",
            "signs of sepsis": "HIGH",
            "severe dehydration": "HIGH"
        }
        
        for flag, level in red_flags.items():
            if flag in chief_complaint:
                escalations.append({
                    "level": level,
                    "reason": f"Red flag present: {flag}",
                    "type": "red_flag_identified",
                    "action": "Immediate escalation required"
                })
        
        metadata = {
            "esi_level": triage_level,
            "triage_category": triage_reason,
            "estimated_wait_time": "Immediate" if triage_level <= 2 else "< 1 hour" if triage_level == 3 else "2-3 hours",
            "requires_monitor": triage_level <= 3
        }
        
        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": metadata,
            "confidence": confidence
        }