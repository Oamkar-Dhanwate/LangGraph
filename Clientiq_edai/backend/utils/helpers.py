# Helper functions
"""
ClientIQ — Helper Utilities
Reusable functions shared across the entire backend.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = str(uuid.uuid4()).replace("-", "")[:16]
    return f"{prefix}_{uid}" if prefix else uid


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    """Return current UTC time as ISO 8601 string."""
    return utc_now().isoformat()


def truncate_text(text: str, max_chars: int = 500) -> str:
    """Safely truncate text with ellipsis."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def clean_text(text: str) -> str:
    """Remove excess whitespace and normalize newlines."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_json_loads(raw: str, default: Any = None) -> Any:
    """Parse JSON without raising on malformed input."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def flatten_list(nested: List[List]) -> List:
    """Flatten one level of nesting."""
    return [item for sublist in nested for item in sublist]


def compute_text_hash(text: str) -> str:
    """Return SHA-256 hash of text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_citation(source: str, chunk_id: str, score: float, excerpt: str) -> Dict:
    """Build a standard citation object for responses."""
    return {
        "source": source,
        "chunk_id": chunk_id,
        "score": round(score, 4),
        "excerpt": truncate_text(excerpt, 200),
        "retrieved_at": utc_now_str(),
    }


def calculate_health_score(
    sentiment_avg: float,
    ticket_count: int,
    days_since_contact: int,
    contract_value: float,
    renewal_days: int,
) -> float:
    """
    Compute a 0-100 client health score from multiple signals.

    Higher = healthier client relationship.
    """
    # Normalize sentiment (-1..1) → (0..30)
    sentiment_score = (sentiment_avg + 1) / 2 * 30

    # Ticket volume penalty (0 tickets = 20pts, 10+ tickets = 0)
    ticket_score = max(0, 20 - ticket_count * 2)

    # Recency score (contacted today = 20pts, 90+ days = 0)
    recency_score = max(0, 20 - days_since_contact * 0.22)

    # Contract size bonus (log scale, max 15pts)
    import math
    contract_score = min(15, math.log10(max(1, contract_value)) * 2)

    # Renewal proximity (within 30 days = 0, 180+ days = 15)
    renewal_score = min(15, max(0, renewal_days - 30) / 10)

    total = sentiment_score + ticket_score + recency_score + contract_score + renewal_score
    return round(min(100, max(0, total)), 2)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a number as currency string."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}
    sym = symbols.get(currency, currency + " ")
    if amount >= 1_000_000:
        return f"{sym}{amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"{sym}{amount/1_000:.1f}K"
    return f"{sym}{amount:.2f}"


def paginate(items: List, page: int, page_size: int) -> Dict:
    """Return a paginated slice with metadata."""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }