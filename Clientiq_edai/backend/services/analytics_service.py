# KPI engine
"""
ClientIQ — Analytics Service
Business logic for KPI computation, revenue analysis, and trend generation.
Sits between FastAPI routes and the database layer.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from backend.database.models import (
    Company, Contract, SupportTicket, Email,
    Meeting, HealthSnapshot, SentimentTimeline,
)
from backend.utils.helpers import format_currency
from backend.utils.logger import logger


class AnalyticsService:
    """High-level analytics queries and KPI computations."""

    # ── Portfolio Overview ────────────────────────────────────────────────────

    async def get_portfolio_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        """Compute the top-level KPI numbers for the main dashboard."""
        total_companies  = await db.scalar(select(func.count(Company.id))) or 0
        at_risk          = await db.scalar(
            select(func.count(Company.id)).where(Company.churn_risk > 0.60)
        ) or 0
        avg_health       = await db.scalar(select(func.avg(Company.health_score))) or 70.0
        active_arr       = await db.scalar(
            select(func.sum(Contract.value)).where(Contract.status == "active")
        ) or 0.0
        critical_tickets = await db.scalar(
            select(func.count(SupportTicket.id)).where(
                and_(SupportTicket.priority == "critical",
                     SupportTicket.status.in_(["open", "in_progress"]))
            )
        ) or 0

        return {
            "total_clients":          total_companies,
            "at_risk_clients":        at_risk,
            "avg_health_score":       round(float(avg_health), 1),
            "active_contract_value":  float(active_arr),
            "critical_open_tickets":  critical_tickets,
            "healthy_pct":            round(
                (total_companies - at_risk) / max(1, total_companies) * 100, 1
            ),
        }

    # ── Revenue Trend ─────────────────────────────────────────────────────────

    async def get_revenue_trend(
        self, db: AsyncSession, months: int = 6
    ) -> List[Dict[str, Any]]:
        """Monthly revenue aggregation from active contracts."""
        since = datetime.now(timezone.utc) - timedelta(days=30 * months)
        result = await db.execute(
            select(
                func.date_format(Contract.start_date, "%Y-%m").label("month"),
                func.sum(Contract.value).label("total"),
                func.count(Contract.id).label("count"),
            )
            .where(
                and_(Contract.status == "active",
                     Contract.start_date >= since)
            )
            .group_by("month")
            .order_by("month")
        )
        rows = result.all()
        return [
            {"month": r.month, "revenue": float(r.total or 0), "contracts": int(r.count)}
            for r in rows
        ]

    # ── Churn Risk Ranking ────────────────────────────────────────────────────

    async def get_churn_risk_ranking(
        self, db: AsyncSession, min_risk: float = 0.0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Clients ranked by churn risk descending."""
        result = await db.execute(
            select(Company)
            .where(Company.churn_risk >= min_risk)
            .order_by(desc(Company.churn_risk))
            .limit(limit)
        )
        companies = result.scalars().all()
        return [
            {
                "id":           c.id,
                "name":         c.name,
                "industry":     c.industry,
                "account_tier": c.account_tier,
                "health_score": float(c.health_score or 0),
                "churn_risk":   float(c.churn_risk or 0),
                "annual_revenue": float(c.annual_revenue or 0),
            }
            for c in companies
        ]

    # ── Sentiment Timeline ────────────────────────────────────────────────────

    async def get_sentiment_timeline(
        self,
        db: AsyncSession,
        company_id: Optional[str] = None,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Sentiment trend over time, optionally scoped to one company."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = (
            select(SentimentTimeline)
            .where(SentimentTimeline.recorded_at >= since)
            .order_by(SentimentTimeline.recorded_at)
            .limit(500)
        )
        if company_id:
            q = q.where(SentimentTimeline.company_id == company_id)
        result = await db.execute(q)
        rows = result.scalars().all()
        return [
            {
                "date":        r.recorded_at.isoformat() if r.recorded_at else None,
                "score":       float(r.sentiment_score),
                "label":       r.sentiment_label,
                "source_type": r.source_type,
                "company_id":  r.company_id,
            }
            for r in rows
        ]

    # ── Health Distribution ───────────────────────────────────────────────────

    async def get_health_distribution(
        self, db: AsyncSession
    ) -> Dict[str, int]:
        """Count companies in each health bucket."""
        result = await db.execute(select(Company.health_score))
        scores = [float(r[0]) for r in result.all() if r[0] is not None]
        dist = {"healthy": 0, "at_risk": 0, "critical": 0}
        for s in scores:
            if s >= 70:
                dist["healthy"] += 1
            elif s >= 40:
                dist["at_risk"] += 1
            else:
                dist["critical"] += 1
        return dist

    # ── Support SLA Metrics ───────────────────────────────────────────────────

    async def get_support_sla(
        self, db: AsyncSession, days: int = 30
    ) -> Dict[str, Any]:
        """SLA performance: avg response and resolution times."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                func.avg(SupportTicket.first_response_hrs).label("avg_response"),
                func.avg(SupportTicket.resolution_hrs).label("avg_resolution"),
                func.count(SupportTicket.id).label("total"),
                func.sum(
                    func.if_(SupportTicket.status.in_(["open", "in_progress"]), 1, 0)
                ).label("open_count"),
                func.sum(
                    func.if_(SupportTicket.priority == "critical", 1, 0)
                ).label("critical_count"),
            )
            .where(SupportTicket.opened_at >= since)
        )
        row = result.one_or_none()
        return {
            "avg_first_response_hrs": round(float(row.avg_response or 0), 1),
            "avg_resolution_hrs":     round(float(row.avg_resolution or 0), 1),
            "total_tickets":          int(row.total or 0),
            "open_tickets":           int(row.open_count or 0),
            "critical_tickets":       int(row.critical_count or 0),
        }

    # ── Health History for One Company ────────────────────────────────────────

    async def get_company_health_history(
        self, db: AsyncSession, company_id: str, weeks: int = 26
    ) -> List[Dict[str, Any]]:
        """Weekly health snapshots for a specific company."""
        since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        result = await db.execute(
            select(HealthSnapshot)
            .where(
                and_(HealthSnapshot.company_id == company_id,
                     HealthSnapshot.snapshot_date >= since)
            )
            .order_by(HealthSnapshot.snapshot_date)
        )
        snaps = result.scalars().all()
        return [
            {
                "date":        s.snapshot_date.isoformat() if s.snapshot_date else None,
                "health":      float(s.health_score),
                "churn_risk":  float(s.churn_risk),
                "sentiment":   float(s.sentiment_avg or 0),
                "tickets":     int(s.ticket_count or 0),
            }
            for s in snaps
        ]


analytics_service = AnalyticsService()