"""
Embedding Service

Produces vector embeddings for retrieval. Priority order (all free):
  1. sentence-transformers (local, no network after first model download)
  2. Ollama embeddings API (local server, e.g. `nomic-embed-text`) if reachable
  3. Deterministic hashed bag-of-words vector (pure Python/numpy, always works)

The fallback chain means RetrievalEngine never breaks even with zero ML
dependencies installed - just lower semantic quality until a real model is
available, exactly like SemanticMemory's fallback in app/memory.
"""
import hashlib
import logging
from typing import List, Optional

import numpy as np
import httpx

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    ST_AVAILABLE = False

HASHED_DIM = 384  # matches all-MiniLM-L6-v2 output dim so downstream code is dimension-agnostic


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", ollama_url: Optional[str] = None):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self._st_model = None
        self.backend = "hashed_fallback"

        if ST_AVAILABLE:
            try:
                self._st_model = SentenceTransformer(model_name)
                self.backend = "sentence_transformers"
                logger.info(f"EmbeddingService using sentence-transformers ({model_name})")
            except Exception as e:
                logger.warning(f"EmbeddingService: could not load {model_name} locally, will try Ollama/fallback: {e}")

    @property
    def dimension(self) -> int:
        if self._st_model is not None:
            try:
                return self._st_model.get_sentence_embedding_dimension()
            except Exception:
                pass
        return HASHED_DIM

    async def embed(self, text: str) -> np.ndarray:
        if self._st_model is not None:
            try:
                return np.asarray(self._st_model.encode(text, normalize_embeddings=True), dtype=np.float32)
            except Exception as e:
                logger.warning(f"EmbeddingService: sentence-transformers encode failed, trying Ollama: {e}")

        if self.ollama_url:
            vector = await self._embed_via_ollama(text)
            if vector is not None:
                self.backend = "ollama"
                return vector

        return self._hashed_embedding(text)

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        if self._st_model is not None:
            try:
                vectors = self._st_model.encode(texts, normalize_embeddings=True)
                return [np.asarray(v, dtype=np.float32) for v in vectors]
            except Exception as e:
                logger.warning(f"EmbeddingService: batch encode failed, falling back per-item: {e}")
        return [await self.embed(t) for t in texts]

    async def _embed_via_ollama(self, text: str) -> Optional[np.ndarray]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data.get("embedding")
                if embedding:
                    return np.asarray(embedding, dtype=np.float32)
        except Exception as e:
            logger.debug(f"EmbeddingService: Ollama embedding unavailable ({e}); using hashed fallback")
        return None

    def _hashed_embedding(self, text: str) -> np.ndarray:
        """
        Deterministic, dependency-free embedding: hash each token into a
        fixed-size vector bucket. Not semantically rich, but stable,
        reproducible, and good enough to keep retrieval functional with
        zero ML dependencies installed.
        """
        vector = np.zeros(HASHED_DIM, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % HASHED_DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector
