"""
Vector Store

Dual-backend vector store: Qdrant when reachable (production / Docker
Compose), FAISS in-memory index as automatic fallback (local dev with no
Qdrant running, or Qdrant unreachable). Both are exposed through the same
interface so RetrievalEngine doesn't know or care which backend is active.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QdrantClient = None
    QDRANT_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    faiss = None
    FAISS_AVAILABLE = False


class FaissBackend:
    """In-memory fallback vector index. Not persisted across restarts -
    acceptable for a hackathon/local-dev fallback; Qdrant is the durable path."""

    def __init__(self, dimension: int):
        self.dimension = dimension
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(dimension)
        else:
            self.index = None
        self._payloads: List[Dict[str, Any]] = []
        self._vectors: List[np.ndarray] = []  # used only if faiss isn't installed at all

    def upsert(self, vector: np.ndarray, payload: Dict[str, Any]) -> None:
        vector = vector.astype(np.float32).reshape(1, -1)
        if self.index is not None:
            self.index.add(vector)
        else:
            self._vectors.append(vector[0])
        self._payloads.append(payload)

    def search(self, vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._payloads:
            return []
        vector = vector.astype(np.float32).reshape(1, -1)

        if self.index is not None:
            scores, indices = self.index.search(vector, min(top_k, len(self._payloads)))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                results.append({"score": float(score), **self._payloads[idx]})
            return results

        # Pure-numpy fallback if faiss itself isn't installed
        scored = []
        for i, v in enumerate(self._vectors):
            denom = (np.linalg.norm(v) * np.linalg.norm(vector[0])) or 1e-9
            score = float(np.dot(v, vector[0]) / denom)
            scored.append((score, self._payloads[i]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, **p} for s, p in scored[:top_k]]


class VectorStore:
    def __init__(self, dimension: int, qdrant_url: Optional[str] = None, collection_name: str = "medical_guidelines"):
        self.dimension = dimension
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self._qdrant: Optional["QdrantClient"] = None
        self.backend = "faiss_fallback"
        self._faiss_backend = FaissBackend(dimension)

    async def connect(self) -> str:
        if QDRANT_AVAILABLE and self.qdrant_url:
            try:
                self._qdrant = QdrantClient(url=self.qdrant_url, timeout=3.0)
                self._qdrant.get_collections()
                existing = [c.name for c in self._qdrant.get_collections().collections]
                if self.collection_name not in existing:
                    self._qdrant.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                    )
                self.backend = "qdrant"
                logger.info(f"VectorStore connected to Qdrant at {self.qdrant_url}")
            except Exception as e:
                logger.warning(f"VectorStore: Qdrant unreachable ({e}); using in-memory FAISS fallback")
                self._qdrant = None
                self.backend = "faiss_fallback"
        return self.backend

    def upsert(self, vector: np.ndarray, payload: Dict[str, Any], point_id: Optional[str] = None) -> None:
        point_id = point_id or str(uuid.uuid4())
        if self._qdrant is not None:
            try:
                self._qdrant.upsert(
                    collection_name=self.collection_name,
                    points=[PointStruct(id=point_id, vector=vector.tolist(), payload=payload)],
                )
                return
            except Exception as e:
                logger.warning(f"VectorStore: Qdrant upsert failed, writing to FAISS fallback instead: {e}")
        self._faiss_backend.upsert(vector, payload)

    def search(self, vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        if self._qdrant is not None:
            try:
                hits = self._qdrant.search(
                    collection_name=self.collection_name, query_vector=vector.tolist(), limit=top_k
                )
                return [{"score": h.score, **(h.payload or {})} for h in hits]
            except Exception as e:
                logger.warning(f"VectorStore: Qdrant search failed, using FAISS fallback: {e}")
        return self._faiss_backend.search(vector, top_k)

    async def health_check(self) -> Dict[str, Any]:
        return {"backend": self.backend, "qdrant_available": QDRANT_AVAILABLE, "faiss_available": FAISS_AVAILABLE}
