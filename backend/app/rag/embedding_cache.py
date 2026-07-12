"""
Embedding Cache

Wraps EmbeddingService with a content-hash keyed cache so repeated queries
(the same diagnosis text gets re-embedded by MedicalResearchAgent and
EvidenceAgent within the same consultation, and identical guideline seed
documents get re-embedded on every restart) don't recompute embeddings.
Two tiers: a process-local dict (always available) and, when a RedisCache
is supplied, a persistent cross-restart tier as well.
"""
import hashlib
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _cache_key(text: str, model_name: str) -> str:
    digest = hashlib.sha256(f"{model_name}:{text}".encode("utf-8")).hexdigest()
    return f"embedding_cache:{digest}"


class CachedEmbeddingService:
    def __init__(self, embedding_service, redis_cache=None):
        self.embedding_service = embedding_service
        self.redis_cache = redis_cache
        self._local_cache: dict = {}

    @property
    def dimension(self) -> int:
        return self.embedding_service.dimension

    @property
    def backend(self) -> str:
        return self.embedding_service.backend

    async def embed(self, text: str) -> np.ndarray:
        key = _cache_key(text, self.embedding_service.model_name)

        if key in self._local_cache:
            return self._local_cache[key]

        if self.redis_cache:
            try:
                cached = await self.redis_cache.get(key)
                if cached is not None:
                    vector = np.asarray(cached, dtype=np.float32)
                    self._local_cache[key] = vector
                    return vector
            except Exception as e:
                logger.debug(f"CachedEmbeddingService: redis cache read failed ({e})")

        vector = await self.embedding_service.embed(text)
        self._local_cache[key] = vector

        if self.redis_cache:
            try:
                await self.redis_cache.set(key, vector.tolist(), ttl_seconds=7 * 24 * 3600)
            except Exception as e:
                logger.debug(f"CachedEmbeddingService: redis cache write failed ({e})")

        return vector

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]

    def cache_stats(self) -> dict:
        return {"local_cache_size": len(self._local_cache)}
