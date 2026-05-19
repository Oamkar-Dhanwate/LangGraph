# Analytics routes
"""
ClientIQ — Analytics Routes
KPIs, revenue trends, churn risk summaries, and sentiment timelines.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from datetime import datetime, timedelta

from backend.database.connection import get_db
from backend.database.models import Company, SupportTicket, HealthSnapshot, SentimentTimeline, Contract
from backend.api.routes_auth import get_current_user
from backend.utils.logger import logger

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard overview: key metrics summary."""
    # Total companies
    total_companies = await db.scalar(select(func.count(Company.id)))

    # High-risk clients (churn_risk > 0.6)
    at_risk = await db.scalar(
        select(func.count(Company.id)).where(Company.churn_risk > 0.60)
    )

    # Active contracts value
    contract_value = await db.scalar(
        select(func.sum(Contract.value)).where(Contract.status == "active")
    ) or 0

    # Open critical tickets
    critical_tickets = await db.scalar(
        select(func.count(SupportTicket.id)).where(
            SupportTicket.priority == "critical",
            SupportTicket.status.in_(["open", "in_progress"]),
        )
    )

    # Avg health score
    avg_health = await db.scalar(select(func.avg(Company.health_score))) or 70.0

    return {
        "total_clients": total_companies or 0,
        "at_risk_clients": at_risk or 0,
        "active_contract_value": float(contract_value),
        "critical_open_tickets": critical_tickets or 0,
        "avg_health_score": round(float(avg_health), 1),
    }


@router.get("/churn-risk")
async def churn_risk_list(
    limit: int = Query(20, le=100),
    min_risk: float = Query(0.0),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return companies sorted by churn risk."""
    result = await db.execute(
        select(Company)
        .where(Company.churn_risk >= min_risk)
        .order_by(desc(Company.churn_risk))
        .limit(limit)
    )
    companies = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "churn_risk": float(c.churn_risk),
            "health_score": float(c.health_score),
            "industry": c.industry,
            "account_tier": c.account_tier,
        }
        for c in companies
    ]


@router.get("/revenue-trend")
async def revenue_trend(
    months: int = Query(6, ge=1, le=24),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly revenue trend from active contracts."""
    result = await db.execute(
        select(
            func.date_format(Contract.start_date, "%Y-%m").label("month"),
            func.sum(Contract.value).label("total"),
            func.count(Contract.id).label("count"),
        )
        .where(Contract.status == "active")
        .group_by("month")
        .order_by("month")
        .limit(months)
    )
    rows = result.all()
    return [{"month": r.month, "revenue": float(r.total or 0), "contracts": r.count} for r in rows]


@router.get("/sentiment-timeline")
async def sentiment_timeline(
    company_id: Optional[str] = None,
    days: int = Query(90, ge=7, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sentiment trend over time."""
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        select(SentimentTimeline)
        .where(SentimentTimeline.recorded_at >= since)
        .order_by(SentimentTimeline.recorded_at)
        .limit(200)
    )
    if company_id:
        q = q.where(SentimentTimeline.company_id == company_id)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "date": r.recorded_at.isoformat() if r.recorded_at else None,
            "score": float(r.sentiment_score),
            "label": r.sentiment_label,
            "source_type": r.source_type,
        }
        for r in rows
    ]


@router.get("/health-distribution")
async def health_distribution(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Distribution of client health scores in buckets."""
    result = await db.execute(select(Company.health_score))
    scores = [float(r[0]) for r in result.all() if r[0] is not None]

    distribution = {"healthy": 0, "at_risk": 0, "critical": 0}
    for s in scores:
        if s >= 70:
            distribution["healthy"] += 1
        elif s >= 40:
            distribution["at_risk"] += 1
        else:
            distribution["critical"] += 1

    return distribution