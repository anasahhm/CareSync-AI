"""
Retrieval Engine

Central RAG orchestrator: embeds documents/queries via EmbeddingService
(wrapped in CachedEmbeddingService for repeat-query efficiency), stores/
searches dense vectors via VectorStore (Qdrant with automatic FAISS
fallback), and additionally indexes every document into a BM25Index for
hybrid retrieval. Final results are reranked by combining normalized dense
+ BM25 scores, which catches exact clinical terminology matches that a
pure embedding search can miss.
"""
import logging
from typing import List, Dict, Any, Optional

from app.rag.embedding_service import EmbeddingService
from app.rag.embedding_cache import CachedEmbeddingService
from app.rag.vector_store import VectorStore
from app.rag.bm25_index import BM25Index

logger = logging.getLogger(__name__)

DENSE_WEIGHT = 0.65
BM25_WEIGHT = 0.35


def _normalize(scores: List[float]) -> List[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


class RetrievalEngine:
    def __init__(self, qdrant_url: Optional[str] = None, ollama_url: Optional[str] = None, redis_cache=None):
        base_embedding_service = EmbeddingService(ollama_url=ollama_url)
        self.embedding_service = CachedEmbeddingService(base_embedding_service, redis_cache=redis_cache)
        self.vector_store = VectorStore(dimension=self.embedding_service.dimension, qdrant_url=qdrant_url)
        self.bm25_index = BM25Index()
        self._initialized = False

    async def initialize(self) -> Dict[str, Any]:
        backend = await self.vector_store.connect()
        self._initialized = True
        logger.info(
            f"RetrievalEngine initialized (vector backend={backend}, "
            f"embedding backend={self.embedding_service.backend}, hybrid_bm25=enabled)"
        )
        return {"vector_backend": backend, "embedding_backend": self.embedding_service.backend}

    async def index_document(self, text: str, metadata: Dict[str, Any]) -> None:
        vector = await self.embedding_service.embed(text)
        self.vector_store.upsert(vector, payload={"text": text, **metadata})
        self.bm25_index.add_document(text, metadata)

    async def retrieve(self, query: str, top_k: int = 5, kind_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        fetch_k = top_k * 3 if kind_filter else top_k * 2

        vector = await self.embedding_service.embed(query)
        dense_hits = self.vector_store.search(vector, top_k=fetch_k)
        bm25_hits = self.bm25_index.search(query, top_k=fetch_k)

        merged = self._hybrid_rerank(dense_hits, bm25_hits, top_k=fetch_k)

        if kind_filter:
            merged = [r for r in merged if r.get("kind") == kind_filter][:top_k]
        else:
            merged = merged[:top_k]

        return merged

    def _hybrid_rerank(self, dense_hits: List[Dict[str, Any]], bm25_hits: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        dense_scores = _normalize([h.get("score", 0.0) for h in dense_hits])
        bm25_scores = _normalize([h.get("score", 0.0) for h in bm25_hits])

        combined: Dict[str, Dict[str, Any]] = {}

        for hit, norm_score in zip(dense_hits, dense_scores):
            key = hit.get("id") or hit.get("text", "")[:200]
            combined[key] = {**hit, "hybrid_score": norm_score * DENSE_WEIGHT}

        for hit, norm_score in zip(bm25_hits, bm25_scores):
            key = hit.get("id") or hit.get("text", "")[:200]
            if key in combined:
                combined[key]["hybrid_score"] += norm_score * BM25_WEIGHT
            else:
                combined[key] = {**hit, "hybrid_score": norm_score * BM25_WEIGHT}

        ranked = sorted(combined.values(), key=lambda x: x["hybrid_score"], reverse=True)
        return ranked[:top_k]

    async def health_check(self) -> Dict[str, Any]:
        vector_health = await self.vector_store.health_check()
        return {
            **vector_health,
            "embedding_backend": self.embedding_service.backend,
            "embedding_dimension": self.embedding_service.dimension,
            "bm25_document_count": self.bm25_index.size(),
            "embedding_cache": self.embedding_service.cache_stats(),
        }
