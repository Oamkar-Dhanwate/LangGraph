# Document chunking
"""
ClientIQ — Document Chunker
Splits long documents into overlapping chunks suitable for RAG indexing.
Preserves metadata for citation and filtering.
"""

from typing import List, Dict, Any, Optional
from backend.utils.config import settings
from backend.utils.helpers import compute_text_hash
from backend.utils.logger import logger


class DocumentChunk:
    """Represents a single indexable text chunk with metadata."""

    def __init__(
        self,
        text: str,
        chunk_index: int,
        source: str,
        source_type: str,
        source_id: str,
        company_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.source = source
        self.source_type = source_type   # email | meeting | call | contract | ticket
        self.source_id = source_id
        self.company_id = company_id
        self.metadata = metadata or {}
        self.chunk_id = compute_text_hash(f"{source_id}_{chunk_index}")[:24]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id":    self.chunk_id,
            "text":        self.text,
            "chunk_index": self.chunk_index,
            "source":      self.source,
            "source_type": self.source_type,
            "source_id":   self.source_id,
            "company_id":  self.company_id,
            "metadata":    self.metadata,
        }


class Chunker:
    """
    Splits documents into overlapping fixed-size chunks.

    Strategy:
    - Split at sentence boundaries when possible
    - Maintain chunk_size ± 10% tolerance
    - Overlap to preserve context across boundaries
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_document(
        self,
        text: str,
        source: str,
        source_type: str,
        source_id: str,
        company_id: str,
        metadata: Optional[Dict] = None,
    ) -> List[DocumentChunk]:
        """
        Split a document into overlapping chunks.
        Returns list of DocumentChunk objects.
        """
        if not text or not text.strip():
            return []

        text = text.strip()
        chunks_text = self._split(text)

        chunks = []
        for i, chunk_text in enumerate(chunks_text):
            if len(chunk_text.strip()) < 30:  # skip trivially small chunks
                continue
            chunk = DocumentChunk(
                text=chunk_text.strip(),
                chunk_index=i,
                source=source,
                source_type=source_type,
                source_id=source_id,
                company_id=company_id,
                metadata=metadata or {},
            )
            chunks.append(chunk)

        logger.debug("[Chunker] {} → {} chunks (size={}, overlap={})", source_type, len(chunks), self.chunk_size, self.chunk_overlap)
        return chunks

    def _split(self, text: str) -> List[str]:
        """Split text by sentences, then merge to target chunk size."""
        import re
        # Split at sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if not sentences:
            return [text]

        chunks = []
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If adding this sentence exceeds limit, flush current chunk
            if current_len + sentence_len > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Overlap: keep last N chars worth of sentences
                overlap_text = " ".join(current_chunk)
                overlap_start = max(0, len(overlap_text) - self.chunk_overlap)
                overlap_sentences = overlap_text[overlap_start:].split(". ")
                current_chunk = overlap_sentences if overlap_sentences else []
                current_len = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_len += sentence_len + 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def chunk_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[DocumentChunk]:
        """
        Chunk a batch of documents.

        Each document dict must have:
        - text, source, source_type, source_id, company_id
        - optional: metadata dict
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(
                text=doc.get("text", ""),
                source=doc.get("source", ""),
                source_type=doc.get("source_type", ""),
                source_id=doc.get("source_id", ""),
                company_id=doc.get("company_id", ""),
                metadata=doc.get("metadata"),
            )
            all_chunks.extend(chunks)

        logger.info("[Chunker] Batch: {} docs → {} chunks", len(documents), len(all_chunks))
        return all_chunks


chunker = Chunker()