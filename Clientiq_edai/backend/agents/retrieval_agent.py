# Retrieval agent
"""
ClientIQ — Retrieval Agent
Performs hybrid RAG: semantic search via Pinecone + optional SQL context fusion.
Returns ranked, deduplicated chunks to the shared state.
"""

from backend.graph.state import GraphState, RetrievedChunk
from backend.rag.hybrid_retriever import HybridRetriever
from backend.rag.context_fusion import ContextFusion
from backend.utils.logger import logger


class RetrievalAgent:
    """
    Retrieval Agent — Hybrid RAG.

    Combines:
    - Pinecone vector search (semantic similarity)
    - SQL-backed metadata filtering (company, date range, source type)
    - Context fusion (merges and ranks results)
    """

    def __init__(self):
        self.retriever = HybridRetriever()
        self.fusion = ContextFusion()
        self.name = "retrieval_agent"

    def run(self, state: GraphState) -> GraphState:
        """Execute hybrid retrieval and fuse results."""
        logger.info("[Retrieval] Running hybrid RAG for: {}", state["user_query"][:80])

        query = state["user_query"]
        entity_context = state.get("entity_context", {})

        # Build metadata filter from context
        metadata_filter = {}
        if entity_context.get("company_id"):
            metadata_filter["company_id"] = entity_context["company_id"]
        if entity_context.get("source_type"):
            metadata_filter["source_type"] = entity_context["source_type"]

        # Retrieve from Pinecone
        try:
            chunks: list[RetrievedChunk] = self.retriever.retrieve(
                query=query,
                top_k=state.get("routing_metadata", {}).get("top_k", 5),
                metadata_filter=metadata_filter,
            )
            state["retrieved_chunks"] = chunks
            logger.info("[Retrieval] Retrieved {} chunks from Pinecone", len(chunks))
        except Exception as e:
            logger.error("[Retrieval] Pinecone retrieval failed: {}", e)
            state["retrieved_chunks"] = []

        # Fuse: merge SQL results + vector chunks into unified context
        fused = self.fusion.fuse(
            sql_results=state.get("sql_results", []),
            chunks=state.get("retrieved_chunks", []),
            query=query,
        )
        state["fused_context"] = fused

        state["agent_trace"].append(self.name)
        return state