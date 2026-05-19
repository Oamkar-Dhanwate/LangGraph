# Health scores generation
"""
ClientIQ — Health Score Time-Series Generator
Creates realistic 6-month weekly health score histories
for every company with correlated churn risk trends.
"""

import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

random.seed(42)


def health_to_churn(health: float, noise: float = 0.05) -> float:
    """Convert a health score (0–100) to a churn probability (0–1) with noise."""
    base  = 1.0 - (health / 100.0)
    noisy = base + random.gauss(0, noise)
    return round(max(0.01, min(0.99, noisy)), 4)


def _trend_factor(week: int, total_weeks: int, base_health: float) -> float:
    """
    Generate a time-varying drift for the health score.

    - Healthy accounts (health > 65) improve slightly over time
    - At-risk accounts (health < 50) deteriorate over time
    - Mid-range accounts fluctuate
    """
    progress = week / max(1, total_weeks)
    if base_health >= 65:
        # Gradual improvement
        drift = progress * random.uniform(0, 5)
    elif base_health < 50:
        # Steady decline — churn narrative
        drift = -progress * random.uniform(0, 8)
    else:
        # Random walk
        drift = math.sin(progress * math.pi * 2) * 3
    return drift


def generate_health_snapshots(
    companies: List[Dict],
    weeks: int = 26,
) -> List[Dict[str, Any]]:
    """
    Generate weekly health snapshots for each company.

    Args:
        companies:  List of company dicts (must have 'id' and 'health_score')
        weeks:      Number of weeks of history to generate (default 26 = 6 months)

    Returns:
        List of health_snapshot dicts ready for DB insertion
    """
    snapshots: List[Dict[str, Any]] = []
    now = datetime.utcnow()

    for company in companies:
        cid          = company.get("id", "")
        base_health  = float(company.get("health_score", 70) or 70)
        current_health = base_health

        for week in range(weeks):
            # Week 0 = oldest, week (weeks-1) = most recent
            snap_date = now - timedelta(weeks=(weeks - week))

            # Apply trend + random noise
            trend = _trend_factor(week, weeks, base_health)
            noise = random.gauss(0, 4)
            current_health = max(5.0, min(100.0, base_health + trend + noise))

            # Derive correlated signals from health
            churn_risk     = health_to_churn(current_health, noise=0.04)
            sentiment_avg  = round(
                max(-1.0, min(1.0, (current_health - 50) / 100 + random.gauss(0, 0.12))), 4
            )
            ticket_count   = max(0, int(random.gauss(
                15 - current_health / 10, 3
            )))
            engagement_rate = round(
                max(0.0, min(1.0, current_health / 100 + random.gauss(0, 0.1))), 4
            )

            snapshots.append({
                "company_id":     cid,
                "health_score":   round(current_health, 2),
                "churn_risk":     churn_risk,
                "sentiment_avg":  sentiment_avg,
                "ticket_count":   ticket_count,
                "engagement_rate": engagement_rate,
                "snapshot_date":  snap_date.date().isoformat(),
            })

    return snapshots


def generate_sentiment_timeline(
    companies: List[Dict],
    emails: List[Dict] = None,
    meetings: List[Dict] = None,
    calls: List[Dict] = None,
    tickets: List[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Build a sentiment_timeline table from communication records.
    Extracts sentiment_score from each communication and records it.
    """
    records: List[Dict[str, Any]] = []
    company_ids = {c["id"] for c in companies}

    source_map = [
        (emails   or [], "email",   "sent_at"),
        (meetings or [], "meeting", "scheduled_at"),
        (calls    or [], "call",    "called_at"),
        (tickets  or [], "ticket",  "opened_at"),
    ]

    for items, source_type, date_field in source_map:
        for item in items:
            cid  = item.get("company_id", "")
            if cid not in company_ids:
                continue
            score = float(item.get("sentiment_score", 0) or 0)
            label = "positive" if score >= 0.05 else "negative" if score <= -0.05 else "neutral"
            date_str = item.get(date_field)
            if not date_str:
                continue
            records.append({
                "company_id":     cid,
                "source_type":    source_type,
                "source_id":      item.get("id", ""),
                "sentiment_score": score,
                "sentiment_label": label,
                "recorded_at":    date_str,
            })

    return records


if __name__ == "__main__":
    # Quick smoke test
    test_companies = [
        {"id": "c1", "health_score": 80},
        {"id": "c2", "health_score": 35},
    ]
    snaps = generate_health_snapshots(test_companies, weeks=26)
    print(f"Generated {len(snaps)} health snapshots")
    # Show last snapshot for each company
    by_company: Dict[str, List] = {}
    for s in snaps:
        by_company.setdefault(s["company_id"], []).append(s)
    for cid, ss in by_company.items():
        last = ss[-1]
        print(f"  {cid} → health={last['health_score']} churn={last['churn_risk']}")