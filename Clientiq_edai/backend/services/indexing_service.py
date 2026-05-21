"""
ClientIQ — Auto-Indexing Service
=================================
Automatically chunks, embeds, and upserts a newly saved CRM record
into Pinecone immediately after it is committed to TiDB.

Usage (inside routes_admin.py, after db.commit()):
    from backend.services.indexing_service import indexing_service
    await indexing_service.index_record(record, source_type)

Supported source_types: email | meeting | call | ticket | contract
Records of type  opportunity_note  have no free-text body worth indexing,
so they are silently skipped.
"""

import asyncio
from typing import Optional

from backend.rag.chunker import chunker
from backend.rag.embedder import embedder
from backend.rag.pinedone_store import pinecone_store
from backend.utils.logger import logger


# ── helpers to build the document dict from each ORM model ──────────────────

def _doc_from_email(record) -> dict:
    return {
        "text":        f"Subject: {record.subject}\n\n{record.body}",
        "source":      (record.subject or "")[:80],
        "source_type": "email",
        "source_id":   record.id,
        "company_id":  record.company_id,
        "metadata": {
            "direction": record.direction,
            "sent_at":   str(record.sent_at),
            "sentiment": record.sentiment_label,
        },
    }


def _doc_from_meeting(record) -> Optional[dict]:
    notes = record.notes or ""
    if not notes.strip():
        return None          # nothing to embed
    return {
        "text":        f"Meeting: {record.title}\n\nNotes: {notes}",
        "source":      (record.title or "")[:80],
        "source_type": "meeting",
        "source_id":   record.id,
        "company_id":  record.company_id,
        "metadata": {
            "meeting_type":  record.meeting_type,
            "scheduled_at":  str(record.scheduled_at),
        },
    }


def _doc_from_call(record) -> dict:
    return {
        "text":        f"Call Transcript ({record.call_type}):\n{record.transcript}",
        "source":      f"Call transcript {record.id[:8]}",
        "source_type": "call",
        "source_id":   record.id,
        "company_id":  record.company_id,
        "metadata": {
            "call_type":  record.call_type,
            "called_at":  str(record.called_at),
        },
    }


def _doc_from_ticket(record) -> dict:
    return {
        "text": (
            f"Support Ticket [{record.ticket_number}]: {record.title}\n\n"
            f"{record.description}\n\n"
            f"Resolution: {record.resolution or 'Pending'}"
        ),
        "source":      f"Ticket {record.ticket_number}",
        "source_type": "ticket",
        "source_id":   record.id,
        "company_id":  record.company_id,
        "metadata": {
            "priority": record.priority,
            "status":   record.status,
            "category": record.category,
        },
    }


def _doc_from_contract(record) -> Optional[dict]:
    terms = record.terms_text or ""
    if not terms.strip():
        return None          # no body to embed
    return {
        "text": (
            f"Contract: {record.title}\n"
            f"Type: {record.contract_type} | Value: ${float(record.value):,.0f} | Status: {record.status}\n\n"
            f"{terms}"
        ),
        "source":      (record.title or "")[:80],
        "source_type": "contract",
        "source_id":   record.id,
        "company_id":  record.company_id,
        "metadata": {
            "contract_type": record.contract_type,
            "status":        record.status,
            "value":         str(record.value),
        },
    }


_BUILDERS = {
    "email":    _doc_from_email,
    "meeting":  _doc_from_meeting,
    "call":     _doc_from_call,
    "ticket":   _doc_from_ticket,
    "contract": _doc_from_contract,
}


# ── service ──────────────────────────────────────────────────────────────────

class IndexingService:
    """
    Thin async wrapper that runs chunk → embed → upsert in a background
    thread so it never blocks the FastAPI response.
    """

    async def index_record(self, record, source_type: str) -> None:
        """
        Immediately index a single ORM record into Pinecone.

        Parameters
        ----------
        record      : SQLAlchemy ORM instance (Email, Meeting, etc.)
        source_type : one of  email | meeting | call | ticket | contract
                      pass anything else to skip silently
        """
        builder = _BUILDERS.get(source_type)
        if builder is None:
            # opportunity_note / unknown — nothing to embed
            logger.debug("[IndexingService] source_type='{}' skipped (no embedder)", source_type)
            return

        doc = builder(record)
        if doc is None:
            logger.debug("[IndexingService] source_type='{}' id='{}' skipped (empty body)", source_type, record.id)
            return

        # Run the CPU-bound work in a thread pool so it doesn't block the
        # async event loop.
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_index, doc)

    # ── sync internals (runs in thread pool) ─────────────────────────────────

    def _sync_index(self, doc: dict) -> None:
        source_type = doc["source_type"]
        source_id   = doc["source_id"]

        try:
            # 1. Chunk
            chunks = chunker.chunk_document(
                text=doc["text"],
                source=doc["source"],
                source_type=source_type,
                source_id=source_id,
                company_id=doc["company_id"],
                metadata=doc.get("metadata", {}),
            )
            if not chunks:
                logger.warning("[IndexingService] No chunks produced for {} id={}", source_type, source_id)
                return

            # 2. Embed
            texts      = [c.text for c in chunks]
            embeddings = embedder.embed_batch(texts, batch_size=64, show_progress=False)

            # 3. Build Pinecone vectors
            vectors = []
            for chunk, emb in zip(chunks, embeddings):
                vectors.append({
                    "id":     chunk.chunk_id,
                    "values": emb,
                    "metadata": {
                        "text":        chunk.text[:1000],
                        "source":      chunk.source,
                        "source_type": chunk.source_type,
                        "source_id":   chunk.source_id,
                        "company_id":  chunk.company_id,
                        **chunk.metadata,
                    },
                })

            # 4. Upsert to Pinecone
            upserted = pinecone_store.upsert(vectors)
            logger.info(
                "[IndexingService] Auto-indexed {} id={} → {} chunks → {} vectors upserted",
                source_type, source_id, len(chunks), upserted,
            )

        except Exception as exc:
            # Never crash the API route — just log the failure
            logger.error(
                "[IndexingService] Failed to auto-index {} id={}: {}",
                source_type, source_id, exc,
            )


# Module-level singleton
indexing_service = IndexingService()