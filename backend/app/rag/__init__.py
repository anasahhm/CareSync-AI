"""
RAG (Retrieval-Augmented Generation) Layer

Exports: EmbeddingService, VectorStore, RetrievalEngine, GuidelineRetriever,
PubMedRetriever, EvidenceRetriever, CitationEngine, RecommendationValidator,
ContextBuilder, PromptBuilder, and RAGManager (the facade the rest of the
app wires into).
"""
import logging

from app.rag.embedding_service import EmbeddingService
from app.rag.embedding_cache import CachedEmbeddingService
from app.rag.bm25_index import BM25Index
from app.rag.vector_store import VectorStore
from app.rag.retrieval_engine import RetrievalEngine
from app.rag.guideline_retriever import GuidelineRetriever
from app.rag.pubmed_retriever import PubMedRetriever
from app.rag.evidence_retriever import EvidenceRetriever
from app.rag.citation_engine import CitationEngine
from app.rag.recommendation_validator import RecommendationValidator
from app.rag.context_builder import ContextBuilder
from app.rag.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class RAGManager:
    """Single entry point the orchestrator/agents/routes use to reach RAG."""

    def __init__(self, qdrant_url: str, ollama_url: str, enable_pubmed: bool = True, redis_cache=None):
        self.retrieval_engine = RetrievalEngine(qdrant_url=qdrant_url, ollama_url=ollama_url, redis_cache=redis_cache)
        self.evidence_retriever = EvidenceRetriever(self.retrieval_engine, enable_pubmed=enable_pubmed)
        self.guideline_retriever = self.evidence_retriever.guideline_retriever
        self._initialized = False

    async def initialize(self) -> dict:
        status = await self.retrieval_engine.initialize()
        await self.guideline_retriever.seed()
        self._initialized = True
        logger.info("RAGManager initialized")
        return status

    async def health_check(self) -> dict:
        return await self.retrieval_engine.health_check()


__all__ = [
    "EmbeddingService", "CachedEmbeddingService", "BM25Index", "VectorStore", "RetrievalEngine",
    "GuidelineRetriever", "PubMedRetriever", "EvidenceRetriever", "CitationEngine",
    "RecommendationValidator", "ContextBuilder", "PromptBuilder", "RAGManager",
]
