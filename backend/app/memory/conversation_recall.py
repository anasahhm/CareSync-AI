"""
Conversation Recall

Summarizes/compresses a consultation's turn history for agents that need
recent context but shouldn't be handed an unbounded transcript (keeps
prompt/context sizes predictable if/when agents are upgraded to call an
LLM). Pure text heuristics - no model call required.
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

MAX_RAW_TURNS = 6
MAX_SUMMARY_CHARS = 800


class ConversationRecall:
    @staticmethod
    def recent_turns(turns: List[Dict[str, str]], limit: int = MAX_RAW_TURNS) -> List[Dict[str, str]]:
        return turns[-limit:]

    @staticmethod
    def compress(turns: List[Dict[str, str]]) -> str:
        """Deterministic compression: keep first and last few turns verbatim,
        summarize the middle by speaker turn-count only (no hallucinated content)."""
        if not turns:
            return ""

        if len(turns) <= MAX_RAW_TURNS:
            text = " | ".join(f"{t['speaker']}: {t['text']}" for t in turns)
            return text[:MAX_SUMMARY_CHARS]

        head = turns[:2]
        tail = turns[-3:]
        middle_count = len(turns) - len(head) - len(tail)

        head_text = " | ".join(f"{t['speaker']}: {t['text']}" for t in head)
        tail_text = " | ".join(f"{t['speaker']}: {t['text']}" for t in tail)

        compressed = f"{head_text} | [...{middle_count} earlier turn(s) omitted...] | {tail_text}"
        return compressed[:MAX_SUMMARY_CHARS]

    @staticmethod
    def build_agent_context_bundle(turns: List[Dict[str, str]], shared_facts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "recent_turns": ConversationRecall.recent_turns(turns),
            "conversation_summary": ConversationRecall.compress(turns),
            "shared_facts": shared_facts,
        }
