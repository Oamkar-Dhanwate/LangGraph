# Citation agent
"""
ClientIQ — Citation Agent
Builds source citations from retrieved chunks and computes an overall
confidence score for the response.
"""

from typing import List
from backend.graph.state import GraphState, Citation, RetrievedChunk
from backend.utils.helpers import build_citation
from backend.utils.logger import logger


class CitationAgent:
    """
    Citation Agent.

    For each retrieved chunk, produces a structured citation containing:
    - Source document and type
    - Excerpt
    - Relevance score
    - Confidence rolled up to query level
    """

    def __init__(self):
        self.name = "citation_agent"

    def run(self, state: GraphState) -> GraphState:
        """Build citations from all retrieved context."""
        logger.info("[Citation] Building citations from {} chunks", len(state.get("retrieved_chunks", [])))

        chunks: List[RetrievedChunk] = state.get("retrieved_chunks", [])
        citations: List[Citation] = []

        for chunk in chunks:
            citation = build_citation(
                source=chunk.get("source", "Unknown"),
                chunk_id=chunk.get("chunk_id", ""),
                score=chunk.get("score", 0.0),
                excerpt=chunk.get("text", ""),
            )
            citations.append(citation)

        # Add SQL-based citation if we have structured results
        if state.get("sql_results"):
            citations.append({
                "source": "TiDB CRM Database",
                "chunk_id": "sql_result",
                "score": 1.0,
                "excerpt": f"{len(state['sql_results'])} records retrieved from CRM",
                "retrieved_at": "",
            })

        state["citations"] = citations

        # Compute confidence score
        if citations:
            vector_scores = [c["score"] for c in citations if c.get("chunk_id") != "sql_result"]
            avg_score = sum(vector_scores) / len(vector_scores) if vector_scores else 0.5
            # Boost if we have both SQL and vector results
            has_sql = bool(state.get("sql_results"))
            has_vector = bool(state.get("retrieved_chunks"))
            boost = 0.1 if (has_sql and has_vector) else 0.0
            state["confidence_score"] = min(1.0, avg_score + boost)
        else:
            state["confidence_score"] = 0.3  # low confidence without citations

        logger.info(
            "[Citation] {} citations built | confidence={:.2f}",
            len(citations), state["confidence_score"]
        )

        state["agent_trace"].append(self.name)
        return state