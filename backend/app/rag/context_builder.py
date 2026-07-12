"""
Context Builder

Assembles the full context bundle an agent (or, in the future, an LLM
prompt) needs: patient/consultation facts, conversation recall, retrieved
evidence, and prior agent outputs from shared memory. Single place that
decides "what does downstream reasoning get to see" so it's consistent
whether it's read by a rule-based agent today or an LLM-backed one later.
"""
import logging
from typing import Dict, Any, Optional

from app.memory.conversation_recall import ConversationRecall

logger = logging.getLogger(__name__)


class ContextBuilder:
    @staticmethod
    async def build(
        context,
        evidence_bundle: Optional[Dict[str, Any]] = None,
        memory_manager=None,
    ) -> Dict[str, Any]:
        bundle: Dict[str, Any] = {
            "consultation_id": context.consultation_id,
            "patient_id": context.patient_id,
            "chief_complaint": context.chief_complaint,
            "doctor_notes": context.doctor_notes,
            "medical_history": context.medical_history,
            "current_medications": context.patient_current_medications,
            "allergies": context.patient_allergies,
            "patient_age": context.patient_age,
        }

        if evidence_bundle:
            bundle["evidence"] = evidence_bundle

        if memory_manager:
            try:
                turns = await memory_manager.consultation_memory.get_turns(context.consultation_id)
                shared_facts = await memory_manager.shared_memory.read_all(context.consultation_id)
                bundle["conversation"] = ConversationRecall.build_agent_context_bundle(turns, shared_facts)
            except Exception as e:
                logger.warning(f"ContextBuilder: could not attach memory context (non-fatal): {e}")

        return bundle
