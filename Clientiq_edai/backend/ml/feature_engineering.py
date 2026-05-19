# Feature engineering
"""
ClientIQ — Feature Engineering
Transforms raw CRM records and communication signals into
ML-ready feature vectors for churn and risk models.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.utils.logger import logger


class FeatureEngineer:
    """
    Converts heterogeneous CRM data into a normalised numeric feature dict.

    Feature Groups:
      - Engagement: days_since_contact, email_frequency, meeting_count
      - Health:     health_score, sentiment_avg
      - Support:    ticket_count, open_tickets, avg_resolution_hrs, critical_tickets
      - Financial:  contract_value_log, renewal_days, account_age_months
      - Risk:       composite_risk_score
    """

    def extract(
        self,
        company_row: Dict[str, Any],
        emails: List[Dict] = None,
        meetings: List[Dict] = None,
        tickets: List[Dict] = None,
        contracts: List[Dict] = None,
    ) -> Dict[str, float]:
        """
        Build the full feature vector for one company.

        Args:
            company_row:  Row from companies table (dict)
            emails:       List of email dicts for this company
            meetings:     List of meeting dicts
            tickets:      List of support_ticket dicts
            contracts:    List of contract dicts

        Returns:
            Dict[feature_name -> float value]
        """
        emails    = emails    or []
        meetings  = meetings  or []
        tickets   = tickets   or []
        contracts = contracts or []

        features: Dict[str, float] = {}

        # ── Health & Sentiment ───────────────────────────────────────────────
        features["health_score"] = float(company_row.get("health_score", 70) or 70)

        sentiment_scores = (
            [float(e.get("sentiment_score", 0)) for e in emails  if e.get("sentiment_score") is not None] +
            [float(m.get("sentiment_score", 0)) for m in meetings if m.get("sentiment_score") is not None] +
            [float(t.get("sentiment_score", 0)) for t in tickets  if t.get("sentiment_score") is not None]
        )
        features["sentiment_avg"] = (
            sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        )
        features["sentiment_volatility"] = self._std(sentiment_scores)

        # ── Engagement ───────────────────────────────────────────────────────
        features["email_count"]   = float(len(emails))
        features["meeting_count"] = float(len(meetings))

        # Inbound vs outbound email ratio (high inbound = more client-initiated = engagement)
        inbound = sum(1 for e in emails if e.get("direction") == "inbound")
        features["inbound_email_ratio"] = inbound / max(1, len(emails))

        # Days since last contact (emails + meetings)
        contact_dates = (
            [self._parse_dt(e.get("sent_at"))      for e in emails   if e.get("sent_at")]  +
            [self._parse_dt(m.get("scheduled_at")) for m in meetings if m.get("scheduled_at")]
        )
        valid_dates = [d for d in contact_dates if d]
        if valid_dates:
            most_recent = max(valid_dates)
            now         = datetime.now(timezone.utc)
            delta       = (now - most_recent).days
            features["days_since_contact"] = float(delta)
        else:
            features["days_since_contact"] = 90.0   # default penalty

        # ── Support Signals ──────────────────────────────────────────────────
        features["ticket_count"]    = float(len(tickets))
        open_tix = [t for t in tickets if t.get("status") in ("open", "in_progress")]
        features["open_tickets"]    = float(len(open_tix))
        features["critical_tickets"]= float(sum(1 for t in tickets if t.get("priority") == "critical"))

        res_hrs = [float(t["resolution_hrs"]) for t in tickets if t.get("resolution_hrs")]
        features["avg_resolution_hrs"] = sum(res_hrs) / len(res_hrs) if res_hrs else 24.0

        resp_hrs = [float(t["first_response_hrs"]) for t in tickets if t.get("first_response_hrs")]
        features["avg_first_response_hrs"] = sum(resp_hrs) / len(resp_hrs) if resp_hrs else 8.0

        # Negative ticket sentiment ratio
        neg_tix = sum(1 for t in tickets if float(t.get("sentiment_score", 0)) < -0.2)
        features["negative_ticket_ratio"] = neg_tix / max(1, len(tickets))

        # ── Contract / Financial ─────────────────────────────────────────────
        active_contracts = [c for c in contracts if c.get("status") == "active"]
        contract_value   = sum(float(c.get("value", 0) or 0) for c in active_contracts)
        features["contract_value_log"] = math.log10(max(1.0, contract_value))
        features["active_contract_count"] = float(len(active_contracts))

        # Days until earliest renewal
        now_dt    = datetime.now(timezone.utc)
        end_dates = [self._parse_dt(c.get("end_date")) for c in active_contracts if c.get("end_date")]
        valid_end = [d for d in end_dates if d and d > now_dt]
        if valid_end:
            nearest_renewal = min(valid_end)
            features["renewal_days"] = float((nearest_renewal - now_dt).days)
        else:
            features["renewal_days"] = 365.0

        # Account age
        created = self._parse_dt(company_row.get("created_at"))
        features["account_age_months"] = (
            float((now_dt - created).days / 30) if created else 12.0
        )

        # ── Engagement Rate (composite) ──────────────────────────────────────
        # Higher = more engaged client
        touch_points = len(emails) + len(meetings) * 2
        age_months   = max(1, features["account_age_months"])
        features["engagement_rate"] = min(1.0, touch_points / (age_months * 5))

        # ── Log-transform heavy-tailed features ──────────────────────────────
        for k in ("email_count", "meeting_count", "ticket_count", "open_tickets"):
            features[f"{k}_log"] = math.log1p(features[k])

        return features

    def extract_batch(
        self,
        companies: List[Dict],
        emails_by_company:   Dict[str, List] = None,
        meetings_by_company: Dict[str, List] = None,
        tickets_by_company:  Dict[str, List] = None,
        contracts_by_company:Dict[str, List] = None,
    ) -> List[Dict[str, float]]:
        """Extract features for a list of companies."""
        emails_by   = emails_by_company   or {}
        meetings_by = meetings_by_company or {}
        tickets_by  = tickets_by_company  or {}
        contracts_by= contracts_by_company or {}

        results = []
        for c in companies:
            cid = c.get("id", "")
            feat = self.extract(
                company_row=c,
                emails=emails_by.get(cid, []),
                meetings=meetings_by.get(cid, []),
                tickets=tickets_by.get(cid, []),
                contracts=contracts_by.get(cid, []),
            )
            feat["company_id"] = cid
            results.append(feat)
        return results

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_dt(self, val) -> Optional[datetime]:
        """Parse ISO string or datetime object to tz-aware datetime."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def _std(self, values: List[float]) -> float:
        """Population standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    def get_feature_names(self) -> List[str]:
        """Return ordered list of feature names produced by extract()."""
        return [
            "health_score", "sentiment_avg", "sentiment_volatility",
            "email_count", "meeting_count", "inbound_email_ratio",
            "days_since_contact", "ticket_count", "open_tickets",
            "critical_tickets", "avg_resolution_hrs", "avg_first_response_hrs",
            "negative_ticket_ratio", "contract_value_log", "active_contract_count",
            "renewal_days", "account_age_months", "engagement_rate",
            "email_count_log", "meeting_count_log", "ticket_count_log", "open_tickets_log",
        ]


feature_engineer = FeatureEngineer()