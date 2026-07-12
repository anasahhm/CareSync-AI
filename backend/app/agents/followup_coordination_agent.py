"""
Follow-up Coordination Agent

Schedules follow-up appointments and monitoring plans.
Depends on Treatment Recommendation and Triage agents.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class FollowupCoordinationAgent(BaseAgent):
    AGENT_TYPE = "FOLLOWUP_COORDINATION"
    AGENT_DESCRIPTION = "Schedules follow-ups and coordinates monitoring"
    DEPENDENCIES = ["TREATMENT_RECOMMENDATION", "TRIAGE_ESCALATION", "EXPLANATION", "ESCALATION"]
    TIMEOUT_SECONDS = 15
    
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """Coordinate follow-up care and monitoring"""
        
        recommendations = []
        escalations = []
        confidence = 0.85
        metadata = {}
        
        chief_complaint = (context.chief_complaint or "").lower()
        
        # Determine appropriate follow-up interval based on condition
        follow_up_interval = 14  # Default 2 weeks
        follow_up_type = "In-office or Telemedicine"
        
        # Acute conditions - shorter follow-up
        if any(x in chief_complaint for x in ["sprain", "strain", "minor injury", "acute pain"]):
            follow_up_interval = 7  # 1 week
            follow_up_type = "Telemedicine check-in"
            recommendations.append({
                "type": "followup_plan",
                "text": f"Schedule follow-up in {follow_up_interval} days via telemedicine.",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Acute condition requires short-term follow-up"]
            })
        
        # Chronic conditions - longer structured follow-up
        elif any(x in str(context.medical_history).lower() for x in ["diabetes", "hypertension", "asthma"]):
            follow_up_interval = 30  # 1 month
            follow_up_type = "In-person office visit"
            recommendations.append({
                "type": "chronic_care_plan",
                "text": "Chronic disease management: Schedule monthly follow-ups with physician.",
                "confidence": 0.85,
                "priority": "HIGH",
                "evidence": ["Chronic disease requires regular monitoring"]
            })
        
        # Moderate issues - standard follow-up
        else:
            follow_up_interval = 14  # 2 weeks
            follow_up_type = "Phone or Telemedicine"
            recommendations.append({
                "type": "followup_plan",
                "text": f"Schedule follow-up in {follow_up_interval} days.",
                "confidence": 0.85,
                "priority": "MEDIUM",
                "evidence": ["Standard follow-up interval"]
            })
        
        # Calculate suggested follow-up date
        follow_up_date = datetime.utcnow() + timedelta(days=follow_up_interval)
        
        recommendations.append({
            "type": "appointment_details",
            "text": f"Suggested follow-up date: {follow_up_date.strftime('%B %d, %Y')}",
            "confidence": 0.8,
            "priority": "MEDIUM",
            "evidence": ["Date calculated from clinical protocol"]
        })
        
        # Monitoring plan based on condition
        if "pain" in chief_complaint:
            recommendations.append({
                "type": "monitoring_plan",
                "text": "Monitor: Pain level daily. Record in symptom diary. Report worsening.",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Pain management requires monitoring"]
            })
            
            recommendations.append({
                "type": "warning_signs",
                "text": "Seek immediate care if: Pain worsens, swelling increases, fever develops, or numbness occurs.",
                "confidence": 0.9,
                "priority": "HIGH",
                "evidence": ["Red flags require urgent evaluation"]
            })
        
        # Physical therapy follow-up
        recommendations.append({
            "type": "therapy_plan",
            "text": "Physical therapy: 2-3 sessions/week for 4-6 weeks as tolerated.",
            "confidence": 0.8,
            "priority": "MEDIUM",
            "evidence": ["Evidence-based rehabilitation protocol"]
        })
        
        # Medication follow-up if prescribed
        recommendations.append({
            "type": "medication_monitoring",
            "text": "Monitor medication response: Take as prescribed. Report side effects.",
            "confidence": 0.85,
            "priority": "HIGH",
            "evidence": ["Medication compliance important for outcomes"]
        })
        
        # Lab work if needed
        if any(x in chief_complaint or str(context.medical_history).lower() for x in ["diabetes", "infection", "fever", "inflammation"]):
            recommendations.append({
                "type": "testing",
                "text": "Consider lab work at follow-up: CBC, CMP, or inflammatory markers as appropriate.",
                "confidence": 0.75,
                "priority": "MEDIUM",
                "evidence": ["Monitoring labs indicated for conditions"]
            })
        
        # Specialist referral coordination if needed
        recommendations.append({
            "type": "specialist_coordination",
            "text": "If specialist referral needed, care coordinator will contact insurance and schedule.",
            "confidence": 0.8,
            "priority": "MEDIUM",
            "evidence": ["Care coordination service available"]
        })
        
        # Patient education
        recommendations.append({
            "type": "patient_education",
            "text": "Patient materials: Condition overview, self-care tips, and exercise instructions sent via patient portal.",
            "confidence": 0.85,
            "priority": "MEDIUM",
            "evidence": ["Empowering patients improves outcomes"]
        })
        
        # Care coordination
        recommendations.append({
            "type": "care_coordination",
            "text": "Care team will coordinate with any other treating providers for continuity of care.",
            "confidence": 0.8,
            "priority": "MEDIUM",
            "evidence": ["Care coordination improves patient outcomes"]
        })
        
        # Escalation if high-risk
        if any(x in chief_complaint for x in ["severe", "critical", "emergency"]):
            escalations.append({
                "level": "HIGH",
                "reason": "Complex condition requires close follow-up monitoring",
                "type": "high_risk_followup",
                "action": "Weekly telehealth check-ins and low threshold for in-person evaluation"
            })
        
        # Escalation for non-compliance risk
        recommendations.append({
            "type": "compliance_support",
            "text": "Patient support: Reminders sent via SMS/email for appointments and medications.",
            "confidence": 0.8,
            "priority": "MEDIUM",
            "evidence": ["Compliance support improves adherence"]
        })
        
        metadata = {
            "follow_up_interval_days": follow_up_interval,
            "follow_up_date": follow_up_date.isoformat(),
            "follow_up_type": follow_up_type,
            "monitoring_required": True,
            "therapy_recommended": "pain" in chief_complaint or "injury" in chief_complaint
        }
        
        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": metadata,
            "confidence": confidence
        }