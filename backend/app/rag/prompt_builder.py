"""
Prompt Builder

Turns a ContextBuilder bundle into a structured prompt string, ready for
any free local LLM (Ollama/Llama/Mistral/Qwen/etc. via HTTP) if/when an
agent is upgraded from rule-based heuristics to LLM-backed reasoning. Not
currently called by any agent (none call an LLM yet) - this is the seam
for that upgrade, kept deterministic and dependency-free.
"""
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

SYSTEM_PREAMBLE = (
    "You are a clinical decision-support assistant. Use only the provided "
    "context and evidence. Cite sources when giving a recommendation. If "
    "evidence is insufficient, say so explicitly rather than guessing."
)


class PromptBuilder:
    @staticmethod
    def build_diagnostic_prompt(context_bundle: Dict[str, Any]) -> str:
        lines = [SYSTEM_PREAMBLE, "", "## Patient Context"]
        lines.append(f"Chief complaint: {context_bundle.get('chief_complaint') or 'not provided'}")
        lines.append(f"Doctor notes: {context_bundle.get('doctor_notes') or 'not provided'}")
        lines.append(f"Age: {context_bundle.get('patient_age') or 'unknown'}")
        lines.append(f"Medical history: {json.dumps(context_bundle.get('medical_history') or {})}")
        lines.append(f"Current medications: {', '.join(context_bundle.get('current_medications') or []) or 'none reported'}")
        lines.append(f"Allergies: {', '.join(context_bundle.get('allergies') or []) or 'none reported'}")

        conversation = context_bundle.get("conversation")
        if conversation:
            lines += ["", "## Conversation Summary", conversation.get("conversation_summary", "")]

        evidence = context_bundle.get("evidence")
        if evidence:
            lines += ["", "## Retrieved Evidence"]
            for hit in evidence.get("guideline_hits", []):
                lines.append(f"- [{hit.get('source')}] {hit.get('text')}")
            for hit in evidence.get("pubmed_hits", []):
                lines.append(f"- [PubMed] {hit.get('title')} ({hit.get('pubdate')})")

        lines += ["", "## Task", "Provide a ranked differential diagnosis with a confidence score (0-1) for each, citing the evidence above where applicable."]
        return "\n".join(lines)
