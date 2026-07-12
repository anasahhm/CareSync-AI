"""
Semantic Memory

Embedding-backed similarity search over past consultation notes/recommendations
for a patient, so agents can recall "have we seen something like this before"
without an exact keyword match. Uses sentence-transformers when installed;
falls back to a deterministic bag-of-words cosine similarity (pure Python,
no dependency) so the feature still works with zero extra installs - just
lower recall quality until the real embedding model is installed.
"""
import logging
import math
import re
from collections import Counter
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    _MODEL_NAME = "all-MiniLM-L6-v2"
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

MAX_ENTRIES_PER_SCOPE = 200


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _bow_vector(text: str) -> Counter:
    return Counter(_tokenize(text))


def _bow_cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticMemory:
    """
    In-process semantic index. Entries are (id, text, metadata) tuples kept
    in a flat list - fine for a single patient's history (dozens of entries),
    not intended as a general-purpose vector database (that's RAG's
    RetrievalEngine, which backs onto Qdrant/FAISS for the medical corpus).
    """

    def __init__(self):
        self._model = None
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._model = SentenceTransformer(_MODEL_NAME)
                logger.info(f"SemanticMemory using sentence-transformers model {_MODEL_NAME}")
            except Exception as e:
                logger.warning(f"SemanticMemory: failed to load sentence-transformers model, using BOW fallback: {e}")
                self._model = None
        self._entries: Dict[str, List[Tuple[str, Any, Any]]] = {}

    def add(self, scope_id: str, entry_id: str, text: str, metadata: Dict[str, Any] = None) -> None:
        vector = self._embed(text)
        entries = self._entries.setdefault(scope_id, [])
        entries.append((entry_id, vector, {"text": text, **(metadata or {})}))
        if len(entries) > MAX_ENTRIES_PER_SCOPE:
            # Evict oldest entries first - keeps the most recent history,
            # which is what "similar past visits" retrieval actually needs.
            del entries[: len(entries) - MAX_ENTRIES_PER_SCOPE]

    def search(self, scope_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        entries = self._entries.get(scope_id, [])
        if not entries:
            return []
        query_vector = self._embed(query)

        scored = []
        for entry_id, vector, metadata in entries:
            score = self._similarity(query_vector, vector)
            scored.append({"entry_id": entry_id, "score": score, **metadata})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _embed(self, text: str):
        if self._model is not None:
            try:
                return ("dense", self._model.encode(text, normalize_embeddings=True))
            except Exception as e:
                logger.warning(f"SemanticMemory: embedding failed, falling back to BOW: {e}")
        return ("bow", _bow_vector(text))

    def _similarity(self, a, b) -> float:
        kind_a, vec_a = a
        kind_b, vec_b = b
        if kind_a == "dense" and kind_b == "dense":
            try:
                import numpy as np
                denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)) or 1e-9
                return float(np.dot(vec_a, vec_b) / denom)
            except Exception:
                pass
        # Mixed or BOW fallback
        bow_a = vec_a if kind_a == "bow" else Counter()
        bow_b = vec_b if kind_b == "bow" else Counter()
        return _bow_cosine(bow_a, bow_b)
