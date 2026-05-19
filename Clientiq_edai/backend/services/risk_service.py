# sklearn churn prediction
"""
ClientIQ — Risk Service
Orchestrates batch churn prediction by pulling CRM signals from TiDB,
running feature engineering, and scoring every company.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.database.models import Company, Email, Meeting, SupportTicket, Contract
from backend.ml.churn_model import ChurnPredictor
from backend.ml.feature_engineering import FeatureEngineer
from backend.utils.logger import logger


class RiskService:
    """Manages portfolio-level and per-company churn risk scoring."""

    def __init__(self):
        self.predictor = ChurnPredictor()
        self.engineer  = FeatureEngineer()

    # ── Per-company scoring ───────────────────────────────────────────────────

    async def score_company(
        self, db: AsyncSession, company_id: str
    ) -> Dict[str, Any]:
        """
        Pull all signals for one company, engineer features,
        run churn model, return structured risk record.
        """
        company_result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        if not company:
            return {}

        emails    = await self._fetch_emails(db, company_id)
        meetings  = await self._fetch_meetings(db, company_id)
        tickets   = await self._fetch_tickets(db, company_id)
        contracts = await self._fetch_contracts(db, company_id)

        features = self.engineer.extract(
            company_row=company.to_dict(),
            emails=emails,
            meetings=meetings,
            tickets=tickets,
            contracts=contracts,
        )

        churn_prob  = self.predictor.predict_single(features)
        risk_level  = self._classify(churn_prob)
        key_factors = self._top_factors(features, churn_prob)

        return {
            "company_id":       company_id,
            "company_name":     company.name,
            "churn_probability": round(churn_prob, 4),
            "risk_level":        risk_level,
            "key_factors":       key_factors,
            "features":          {k: round(v, 4) for k, v in features.items() if isinstance(v, float)},
            "scored_at":         datetime.now(timezone.utc).isoformat(),
        }

    # ── Portfolio-level batch scoring ─────────────────────────────────────────

    async def score_portfolio(
        self,
        db: AsyncSession,
        limit: int = 200,
        persist: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Score all companies and optionally write churn_risk back to TiDB.

        Args:
            db:      Async database session
            limit:   Max companies to score
            persist: If True, updates companies.churn_risk column

        Returns:
            List of risk records sorted by churn_probability descending
        """
        result   = await db.execute(select(Company).limit(limit))
        companies = result.scalars().all()

        logger.info("[RiskService] Scoring {} companies", len(companies))

        records = []
        for c in companies:
            try:
                record = await self.score_company(db, c.id)
                if record:
                    records.append(record)
                    if persist:
                        await db.execute(
                            update(Company)
                            .where(Company.id == c.id)
                            .values(churn_risk=record["churn_probability"])
                        )
            except Exception as e:
                logger.error("[RiskService] Failed to score {}: {}", c.name, e)

        if persist:
            await db.commit()

        records.sort(key=lambda r: r["churn_probability"], reverse=True)
        logger.info("[RiskService] Portfolio scored | top risk = {:.1%}",
                    records[0]["churn_probability"] if records else 0)
        return records

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _classify(self, prob: float) -> str:
        if prob >= 0.75: return "critical"
        if prob >= 0.50: return "high"
        if prob >= 0.25: return "medium"
        return "low"

    def _top_factors(self, features: Dict, prob: float) -> List[str]:
        """Surface the top 4 risk drivers from feature values."""
        factors = []
        if features.get("health_score", 100) < 40:
            factors.append(f"Low health score ({features['health_score']:.0f}/100)")
        if features.get("sentiment_avg", 0) < -0.3:
            factors.append(f"Negative sentiment trend ({features['sentiment_avg']:.2f})")
        if features.get("ticket_count", 0) > 10:
            factors.append(f"High ticket volume ({features['ticket_count']:.0f} tickets)")
        if features.get("days_since_contact", 0) > 60:
            factors.append(f"No contact in {features['days_since_contact']:.0f} days")
        if features.get("renewal_days", 999) < 30:
            factors.append(f"Renewal due in {features['renewal_days']:.0f} days")
        if features.get("avg_first_response_hrs", 0) > 48:
            factors.append(f"Slow support: avg {features['avg_first_response_hrs']:.0f}h first response")
        if features.get("open_tickets", 0) > 5:
            factors.append(f"{features['open_tickets']:.0f} open unresolved tickets")
        if not factors:
            factors.append("No critical signals — standard monitoring")
        return factors[:4]

    async def _fetch_emails(self, db, cid: str) -> List[Dict]:
        r = await db.execute(select(Email).where(Email.company_id == cid).limit(200))
        return [e.to_dict() for e in r.scalars().all()]

    async def _fetch_meetings(self, db, cid: str) -> List[Dict]:
        r = await db.execute(select(Meeting).where(Meeting.company_id == cid).limit(50))
        return [m.to_dict() for m in r.scalars().all()]

    async def _fetch_tickets(self, db, cid: str) -> List[Dict]:
        r = await db.execute(select(SupportTicket).where(SupportTicket.company_id == cid).limit(100))
        return [t.to_dict() for t in r.scalars().all()]

    async def _fetch_contracts(self, db, cid: str) -> List[Dict]:
        r = await db.execute(select(Contract).where(Contract.company_id == cid).limit(20))
        return [c.to_dict() for c in r.scalars().all()]


risk_service = RiskService()