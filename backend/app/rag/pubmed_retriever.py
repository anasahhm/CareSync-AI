"""
PubMed Retriever

Queries the free, keyless NCBI E-utilities API (esearch + esummary) for
recent literature relevant to a diagnosis/topic. No API key or paid tier
required, though NCBI does ask for an identifying `tool`/`email` param on
high-volume use, which is included below. Fails closed (returns an empty
list) on any network/API error so an unreachable or rate-limited PubMed
never breaks the consultation pipeline - this mirrors the fallback
philosophy used everywhere else in the RAG layer.
"""
import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class PubMedRetriever:
    def __init__(self, tool_name: str = "caresyncai", contact_email: str = "dev@caresyncai.local", timeout: float = 5.0):
        self.tool_name = tool_name
        self.contact_email = contact_email
        self.timeout = timeout

    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                search_resp = await client.get(ESEARCH_URL, params={
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "tool": self.tool_name,
                    "email": self.contact_email,
                })
                search_resp.raise_for_status()
                id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])

                if not id_list:
                    return []

                summary_resp = await client.get(ESUMMARY_URL, params={
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "json",
                    "tool": self.tool_name,
                    "email": self.contact_email,
                })
                summary_resp.raise_for_status()
                summary_data = summary_resp.json().get("result", {})

                results = []
                for pmid in id_list:
                    entry = summary_data.get(pmid)
                    if not entry:
                        continue
                    results.append({
                        "pmid": pmid,
                        "title": entry.get("title", ""),
                        "source": entry.get("source", "PubMed"),
                        "pubdate": entry.get("pubdate", ""),
                        "citation": f"PMID:{pmid} - {entry.get('title', '')} ({entry.get('source', '')}, {entry.get('pubdate', '')})",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })
                return results
        except Exception as e:
            logger.warning(f"PubMedRetriever: search failed for '{query}' ({e}); returning no results")
            return []
