"""
BM25 Index

Pure-Python BM25 keyword scoring (no extra dependency) used alongside dense
vector search for hybrid retrieval - dense embeddings are good at semantic
similarity but can miss exact clinical terminology matches (drug names,
guideline codes) that BM25 catches reliably. Kept intentionally simple
(no Elasticsearch/Lucene) since the corpus size here is small (a curated
guideline set, not millions of documents).
"""
import logging
import math
import re
from collections import defaultdict
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

K1 = 1.5
B = 0.75


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


class BM25Index:
    def __init__(self):
        self._docs: List[Dict[str, Any]] = []  # {"tokens": [...], "payload": {...}}
        self._doc_freq: Dict[str, int] = defaultdict(int)
        self._avg_doc_len = 0.0

    def add_document(self, text: str, payload: Dict[str, Any]) -> None:
        tokens = _tokenize(text)
        self._docs.append({"tokens": tokens, "payload": {"text": text, **payload}})
        for term in set(tokens):
            self._doc_freq[term] += 1
        self._avg_doc_len = sum(len(d["tokens"]) for d in self._docs) / len(self._docs)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._docs:
            return []
        query_terms = _tokenize(query)
        n_docs = len(self._docs)

        scored = []
        for doc in self._docs:
            score = 0.0
            doc_len = len(doc["tokens"]) or 1
            term_counts = defaultdict(int)
            for t in doc["tokens"]:
                term_counts[t] += 1

            for term in query_terms:
                df = self._doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                tf = term_counts.get(term, 0)
                denom = tf + K1 * (1 - B + B * doc_len / (self._avg_doc_len or 1))
                score += idf * ((tf * (K1 + 1)) / (denom or 1))

            if score > 0:
                scored.append({"score": score, **doc["payload"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def size(self) -> int:
        return len(self._docs)
