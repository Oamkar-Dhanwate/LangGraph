# Result fusion
"""
ClientIQ — Context Fusion
Merges SQL structured results and vector retrieved chunks
into a unified, LLM-ready context string.
"""

from typing import List, Dict, Any
from backend.graph.state import RetrievedChunk
from backend.utils.helpers import truncate_text
from backend.utils.logger import logger
import json


class ContextFusion:
    """
    Fuses heterogeneous retrieval results into a coherent context block.

    Strategy:
    - SQL results → structured tabular summary
    - Vector chunks → ranked excerpts with source labels
    - Combined → single markdown-ish context string for the LLM
    """

    def fuse(
        self,
        sql_results: List[Dict[str, Any]],
        chunks: List[RetrievedChunk],
        query: str,
        max_context_chars: int = 4000,
    ) -> str:
        """
        Merge SQL results and vector chunks.
        Returns a single context string.
        """
        parts = []

        # ── SQL section ───────────────────────────────────────────────────────
        if sql_results:
            parts.append("## Structured CRM Data")
            # Limit to first 10 rows for context window
            for i, row in enumerate(sql_results[:10], 1):
                row_str = self._format_row(row)
                parts.append(f"[Record {i}] {row_str}")

        # ── Vector chunks section ─────────────────────────────────────────────
        if chunks:
            parts.append("\n## Retrieved Documents")
            for chunk in chunks:
                source_label = f"[{chunk.get('source_type','doc').upper()}] {chunk.get('source','')}"
                score_label = f"(relevance: {chunk.get('score', 0):.2f})"
                text = truncate_text(chunk.get("text", ""), 400)
                parts.append(f"{source_label} {score_label}\n{text}")

        if not parts:
            return "No relevant context found for this query."

        fused = "\n\n".join(parts)

        # Trim to max context length
        if len(fused) > max_context_chars:
            fused = fused[:max_context_chars] + "\n\n[Context truncated for length]"

        logger.debug("[ContextFusion] Fused {} SQL rows + {} chunks = {} chars", len(sql_results), len(chunks), len(fused))
        return fused

    def _format_row(self, row: Dict) -> str:
        """Format a single SQL row as a readable string."""
        important_keys = ["name", "company_name", "health_score", "churn_risk",
                         "annual_revenue", "status", "priority", "sentiment_score",
                         "value", "stage", "title"]
        parts = []
        for k in important_keys:
            if k in row and row[k] is not None:
                parts.append(f"{k}={row[k]}")
        if not parts:
            # Fall back to all keys
            parts = [f"{k}={v}" for k, v in list(row.items())[:8] if v is not None]
        return " | ".join(parts)