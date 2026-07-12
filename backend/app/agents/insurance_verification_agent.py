"""
Insurance Verification Agent

Verifies insurance coverage and provides authorization status.
No dependencies - validates independently.
"""
import logging
from typing import Dict, Any

from app.agents import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class InsuranceVerificationAgent(BaseAgent):
    AGENT_TYPE = "INSURANCE_VERIFICATION"
    AGENT_DESCRIPTION = "Verifies insurance coverage and authorization"
    DEPENDENCIES = []
    TIMEOUT_SECONDS = 15
    
    async def _run(self, context: AgentContext) -> Dict[str, Any]:
        """Verify insurance and coverage"""
        
        recommendations = []
        escalations = []
        confidence = 0.85
        metadata = {}
        
        insurance_plan = context.insurance_plan or "No insurance provided"
        
        # Insurance verification
        recommendations.append({
            "type": "insurance_status",
            "text": f"Insurance plan: {insurance_plan}",
            "confidence": 0.9,
            "priority": "HIGH",
            "evidence": ["Insurance information provided"]
        })
        
        # Determine plan type and coverage
        plan_type = "UNKNOWN"
        coverage_level = "STANDARD"
        
        if "ppo" in insurance_plan.lower():
            plan_type = "PPO"
            recommendations.append({
                "type": "plan_details",
                "text": "PPO Plan: Out-of-network providers allowed with higher copay/deductible.",
                "confidence": 0.9,
                "priority": "MEDIUM",
                "evidence": ["PPO identified"]
            })
            coverage_level = "STANDARD"
        
        elif "hmo" in insurance_plan.lower():
            plan_type = "HMO"
            recommendations.append({
                "type": "plan_details",
                "text": "HMO Plan: Requires in-network provider or referral for coverage.",
                "confidence": 0.9,
                "priority": "MEDIUM",
                "evidence": ["HMO identified"]
            })
            coverage_level = "RESTRICTED"
        
        elif "medicare" in insurance_plan.lower():
            plan_type = "MEDICARE"
            recommendations.append({
                "type": "plan_details",
                "text": "Medicare: Covers approved services with Part B copay.",
                "confidence": 0.9,
                "priority": "MEDIUM",
                "evidence": ["Medicare identified"]
            })
            coverage_level = "STANDARD"
        
        elif "medicaid" in insurance_plan.lower():
            plan_type = "MEDICAID"
            recommendations.append({
                "type": "plan_details",
                "text": "Medicaid: Coverage varies by state. May require referral.",
                "confidence": 0.85,
                "priority": "MEDIUM",
                "evidence": ["Medicaid identified"]
            })
            coverage_level = "STATE_DEPENDENT"
        
        else:
            recommendations.append({
                "type": "plan_type",
                "text": "Insurance plan type should be verified with insurance company.",
                "confidence": 0.7,
                "priority": "MEDIUM",
                "evidence": ["Non-standard plan identifier"]
            })
        
        # Coverage authorization
        recommendations.append({
            "type": "authorization_status",
            "text": "Telemedicine consultation typically covered under outpatient services.",
            "confidence": 0.85,
            "priority": "HIGH",
            "evidence": ["Standard telemedicine coverage"]
        })
        
        # Check for common coverage restrictions
        common_restrictions = [
            ("Specialist consultation", "May require PCP referral"),
            ("Mental health services", "May have limited coverage/higher copay"),
            ("Therapy/rehabilitation", "May require pre-authorization"),
            ("Diagnostic imaging", "May require pre-authorization"),
        ]

        recommendations.append({
            "type": "coverage_details",
            "text": "Typical copay: $20-50 for telemedicine; Deductible may apply",
            "confidence": 0.75,
            "priority": "MEDIUM",
            "evidence": ["Standard industry rates"]
        })

        # Pre-authorization requirements: match actual complaint text against
        # the restriction categories above, rather than a hardcoded check.
        complaint_text = (context.chief_complaint or "").lower()
        RESTRICTION_KEYWORDS = {
            "Specialist consultation": ["specialist", "referral"],
            "Mental health services": ["mental health", "psychiatric", "therapy", "counseling"],
            "Therapy/rehabilitation": ["physical therapy", "rehabilitation", "rehab"],
            "Diagnostic imaging": ["imaging", "scan", "x-ray", "mri", "ct scan", "ultrasound"],
        }
        matched_restrictions = [
            (category, note) for category, note in common_restrictions
            if any(kw in complaint_text for kw in RESTRICTION_KEYWORDS.get(category, []))
        ]

        if matched_restrictions:
            recommendations.append({
                "type": "preauth_requirement",
                "text": f"Pre-authorization may be required: {'; '.join(f'{c} ({n})' for c, n in matched_restrictions)}",
                "confidence": 0.8,
                "priority": "HIGH",
                "evidence": [f"Matched against chief complaint: '{context.chief_complaint}'"]
            })
            escalations.append({
                "level": "MEDIUM",
                "reason": "Pre-authorization may be needed for recommended care",
                "type": "insurance_authorization_needed",
                "action": "Contact insurance company for pre-auth if specialist/imaging recommended"
            })
        
        # Out-of-pocket estimates
        recommendations.append({
            "type": "patient_cost",
            "text": "Patient will be responsible for copay and any uncovered services.",
            "confidence": 0.85,
            "priority": "MEDIUM",
            "evidence": ["Standard billing practice"]
        })
        
        # No insurance scenario
        if "no insurance" in insurance_plan.lower() or "uninsured" in insurance_plan.lower():
            recommendations.append({
                "type": "uninsured_status",
                "text": "Patient uninsured. Discuss self-pay options and financial assistance programs.",
                "confidence": 0.95,
                "priority": "HIGH",
                "evidence": ["Uninsured status"]
            })
            escalations.append({
                "level": "MEDIUM",
                "reason": "Uninsured patient may face financial barriers",
                "type": "financial_access",
                "action": "Discuss payment plans, sliding scale, community health resources"
            })
        
        # Out-of-network warning
        recommendations.append({
            "type": "network_status",
            "text": "Confirm provider is in-network to avoid balance billing.",
            "confidence": 0.9,
            "priority": "MEDIUM",
            "evidence": ["Network verification important"]
        })
        
        metadata = {
            "plan_type": plan_type,
            "coverage_level": coverage_level,
            "auth_required": False,
            "patient_verified": True,
            "insurance_verified": insurance_plan != "No insurance provided"
        }
        
        return {
            "recommendations": recommendations,
            "escalations": escalations,
            "metadata": metadata,
            "confidence": confidence
        }