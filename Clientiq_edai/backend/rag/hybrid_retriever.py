# SQL + semantic retrieval
"""
ClientIQ — Hybrid Retriever
Combines Pinecone semantic search with SQL metadata pre-filtering
to achieve accurate, context-aware document retrieval.
"""

from typing import List, Dict, Any, Optional
from backend.rag.embedder import embedder
from backend.rag.pinecone_store import pinecone_store
from backend.graph.state import RetrievedChunk
from backend.utils.config import settings
from backend.utils.logger import logger


class HybridRetriever:
    """
    Hybrid Retrieval combining:
    1. Semantic search (Pinecone dense vectors)
    2. Metadata filtering (company_id, source_type, date range)
    3. Score-based reranking and deduplication
    """

    def __init__(self):
        self.top_k = settings.top_k_results

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        metadata_filter: Optional[Dict] = None,
        min_score: float = 0.30,
    ) -> List[RetrievedChunk]:
        """
        Execute hybrid retrieval for a query.

        Args:
            query: Natural language query
            top_k: Number of results to return
            metadata_filter: Pinecone metadata filter dict
            min_score: Minimum cosine similarity threshold

        Returns:
            List of RetrievedChunk objects, ranked by score.
        """
        k = top_k or self.top_k

        # 1. Embed the query
        try:
            query_vector = embedder.embed(query)
        except Exception as e:
            logger.error("[HybridRetriever] Embedding failed: {}", e)
            return []

        # 2. Semantic search in Pinecone
        raw_results = pinecone_store.query(
            vector=query_vector,
            top_k=k * 2,           # over-fetch, then filter
            metadata_filter=metadata_filter,
        )

        # 3. Filter by minimum score
        filtered = [r for r in raw_results if r.get("score", 0) >= min_score]

        # 4. Deduplicate by chunk_id
        seen_ids = set()
        unique = []
        for r in filtered:
            cid = r.get("chunk_id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique.append(r)

        # 5. Convert to typed RetrievedChunk
        chunks: List[RetrievedChunk] = []
        for r in unique[:k]:
            chunk: RetrievedChunk = {
                "chunk_id":    r.get("chunk_id", ""),
                "source":      r.get("source", ""),
                "source_type": r.get("source_type", ""),
                "company_id":  r.get("company_id", ""),
                "text":        r.get("text", ""),
                "score":       r.get("score", 0.0),
            }
            chunks.append(chunk)

        logger.info(
            "[HybridRetriever] Query='{}' | raw={} filtered={} returned={}",
            query[:60], len(raw_results), len(filtered), len(chunks)
        )
        return chunks

    def retrieve_by_company(
        self,
        query: str,
        company_id: str,
        source_types: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        """Retrieve documents scoped to a specific company."""
        filt: Dict[str, Any] = {"company_id": {"$eq": company_id}}
        if source_types:
            filt["source_type"] = {"$in": source_types}
        return self.retrieve(query=query, top_k=top_k, metadata_filter=filt)

    def retrieve_multi_company(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[RetrievedChunk]:
        """Retrieve across all companies — for portfolio-level analysis."""
        return self.retrieve(query=query, top_k=top_k, metadata_filter=None)