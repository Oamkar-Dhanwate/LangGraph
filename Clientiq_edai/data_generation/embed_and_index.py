# Precode indexer
"""
ClientIQ — Pinecone Indexer
Fetches all communication records from TiDB, chunks them,
generates embeddings, and upserts into Pinecone.

Run AFTER seed_all.py:  python -m data_generation.embed_and_index
"""

import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List, Dict, Any
from tqdm import tqdm

from backend.database.connection import get_db_session
from backend.database.models import Email, Meeting, CallTranscript, SupportTicket, Contract
from backend.rag.chunker import chunker
from backend.rag.embedder import embedder
from backend.rag.pinecone_store import pinecone_store
from backend.utils.logger import logger
from sqlalchemy import select


async def fetch_and_index_emails(session) -> int:
    result = await session.execute(select(Email).limit(5000))
    emails = result.scalars().all()
    documents = [
        {
            "text": f"Subject: {e.subject}\n\n{e.body}",
            "source": e.subject[:80],
            "source_type": "email",
            "source_id": e.id,
            "company_id": e.company_id,
            "metadata": {"direction": e.direction, "sent_at": str(e.sent_at), "sentiment": e.sentiment_label},
        }
        for e in emails
    ]
    return _chunk_embed_upsert(documents, "emails")


async def fetch_and_index_meetings(session) -> int:
    result = await session.execute(select(Meeting).limit(2000))
    meetings = result.scalars().all()
    documents = [
        {
            "text": f"Meeting: {m.title}\n\nNotes: {m.notes or ''}",
            "source": m.title[:80],
            "source_type": "meeting",
            "source_id": m.id,
            "company_id": m.company_id,
            "metadata": {"meeting_type": m.meeting_type, "scheduled_at": str(m.scheduled_at)},
        }
        for m in meetings if m.notes
    ]
    return _chunk_embed_upsert(documents, "meetings")


async def fetch_and_index_calls(session) -> int:
    result = await session.execute(select(CallTranscript).limit(1000))
    calls = result.scalars().all()
    documents = [
        {
            "text": f"Call Transcript ({c.call_type}):\n{c.transcript}",
            "source": f"Call transcript {c.id[:8]}",
            "source_type": "call",
            "source_id": c.id,
            "company_id": c.company_id,
            "metadata": {"call_type": c.call_type, "called_at": str(c.called_at)},
        }
        for c in calls
    ]
    return _chunk_embed_upsert(documents, "calls")


async def fetch_and_index_tickets(session) -> int:
    result = await session.execute(select(SupportTicket).limit(3000))
    tickets = result.scalars().all()
    documents = [
        {
            "text": f"Support Ticket [{t.ticket_number}]: {t.title}\n\n{t.description}\n\nResolution: {t.resolution or 'Pending'}",
            "source": f"Ticket {t.ticket_number}",
            "source_type": "ticket",
            "source_id": t.id,
            "company_id": t.company_id,
            "metadata": {"priority": t.priority, "status": t.status, "category": t.category},
        }
        for t in tickets
    ]
    return _chunk_embed_upsert(documents, "tickets")


async def fetch_and_index_contracts(session) -> int:
    result = await session.execute(select(Contract).limit(500))
    contracts = result.scalars().all()
    documents = [
        {
            "text": f"Contract: {c.title}\nType: {c.contract_type} | Value: ${float(c.value):,.0f} | Status: {c.status}\n\n{c.terms_text or ''}",
            "source": c.title[:80],
            "source_type": "contract",
            "source_id": c.id,
            "company_id": c.company_id,
            "metadata": {"contract_type": c.contract_type, "status": c.status, "value": str(c.value)},
        }
        for c in contracts if c.terms_text
    ]
    return _chunk_embed_upsert(documents, "contracts")


def _chunk_embed_upsert(documents: List[Dict], label: str) -> int:
    """Chunk → embed → upsert pipeline for a list of documents."""
    if not documents:
        logger.warning("[Indexer] No {} documents to index", label)
        return 0

    # 1. Chunk
    all_chunks = chunker.chunk_batch(documents)
    logger.info("[Indexer] {} → {} chunks", label, len(all_chunks))

    # 2. Embed in batches
    texts = [c.text for c in all_chunks]
    embeddings = embedder.embed_batch(texts, batch_size=64, show_progress=True)

    # 3. Prepare Pinecone vectors
    vectors = []
    for chunk, emb in zip(all_chunks, embeddings):
        vectors.append({
            "id": chunk.chunk_id,
            "values": emb,
            "metadata": {
                "text":        chunk.text[:1000],  # Pinecone metadata limit
                "source":      chunk.source,
                "source_type": chunk.source_type,
                "source_id":   chunk.source_id,
                "company_id":  chunk.company_id,
                **chunk.metadata,
            },
        })

    # 4. Upsert to Pinecone
    upserted = pinecone_store.upsert(vectors, batch_size=100)
    logger.info("[Indexer] Upserted {} vectors for {}", upserted, label)
    return upserted


async def main():
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║  ClientIQ — Pinecone Indexer                  ║")
    logger.info("╚══════════════════════════════════════════════╝")

    total = 0
    async with get_db_session() as session:
        total += await fetch_and_index_emails(session)
        total += await fetch_and_index_meetings(session)
        total += await fetch_and_index_calls(session)
        total += await fetch_and_index_tickets(session)
        total += await fetch_and_index_contracts(session)

    stats = pinecone_store.get_stats()
    logger.info("Indexing complete | total vectors upserted={}", total)
    logger.info("Pinecone index stats: {}", stats)
    print(f"\n✓ Indexed {total} vectors into Pinecone")
    print(f"  Index: {pinecone_store.index_name}")


if __name__ == "__main__":
    asyncio.run(main())