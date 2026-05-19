# Risk agent
"""
ClientIQ — Risk Prediction Agent
Uses ML (scikit-learn) to predict churn probability and renewal risk
from CRM signals, sentiment trends, and engagement metrics.
"""

from typing import Any, Dict, List
from backend.graph.state import GraphState, RiskScore
from backend.ml.churn_model import ChurnPredictor
from backend.utils.logger import logger


class RiskAgent:
    """
    Risk Prediction Agent.

    For each client in scope, computes:
    - Churn probability (ML model)
    - Risk level classification
    - Key risk factors
    - Renewal timeline alerts
    """

    def __init__(self):
        self.predictor = ChurnPredictor()
        self.name = "risk_agent"

    def run(self, state: GraphState) -> GraphState:
        """Compute risk scores for clients in scope."""
        logger.info("[Risk] Computing churn risk scores")

        sql_results = state.get("sql_results", [])
        risk_scores: List[RiskScore] = []

        for row in sql_results[:20]:  # cap at 20 clients
            company_id = row.get("id") or row.get("company_id")
            company_name = row.get("name") or row.get("company_name", "Unknown")

            if not company_id:
                continue

            # Extract features from CRM row
            features = self._extract_features(row, state)

            # Predict churn probability
            churn_prob = self.predictor.predict_single(features)
            risk_level = self._classify_risk(churn_prob)
            key_factors = self._identify_factors(features, churn_prob)
            actions = self._suggest_actions(risk_level, key_factors)

            risk_score: RiskScore = {
                "company_id": str(company_id),
                "company_name": company_name,
                "churn_probability": round(churn_prob, 4),
                "risk_level": risk_level,
                "key_factors": key_factors,
                "recommended_actions": actions,
            }
            risk_scores.append(risk_score)

        # Sort by highest risk first
        risk_scores.sort(key=lambda r: r["churn_probability"], reverse=True)

        state["risk_scores"] = risk_scores
        state["agent_trace"].append(self.name)

        logger.info("[Risk] Computed {} risk scores | {} high risk", len(risk_scores), sum(1 for r in risk_scores if r["risk_level"] in ["high", "critical"]))
        return state

    def _extract_features(self, row: Dict, state: GraphState) -> Dict[str, float]:
        """Convert CRM row + state signals into ML features."""
        sentiment_avg = float(row.get("sentiment_avg") or state.get("sentiment_score", 0))

        return {
            "health_score":       float(row.get("health_score", 70)),
            "sentiment_avg":      sentiment_avg,
            "ticket_count":       float(row.get("ticket_count", 0)),
            "days_since_contact": float(row.get("days_since_contact", 30)),
            "contract_value":     float(row.get("value") or row.get("annual_revenue") or 50000),
            "renewal_days":       float(row.get("renewal_days", 180)),
            "open_tickets":       float(row.get("open_tickets", 0)),
            "avg_response_hrs":   float(row.get("first_response_hrs") or 24),
            "engagement_rate":    float(row.get("engagement_rate") or 0.5),
            "account_age_months": float(row.get("account_age_months", 12)),
        }

    def _classify_risk(self, prob: float) -> str:
        if prob >= 0.75:
            return "critical"
        elif prob >= 0.50:
            return "high"
        elif prob >= 0.25:
            return "medium"
        return "low"

    def _identify_factors(self, features: Dict, prob: float) -> List[str]:
        """Surface the top contributing risk factors."""
        factors = []
        if features["health_score"] < 40:
            factors.append("Very low health score")
        if features["sentiment_avg"] < -0.3:
            factors.append("Negative sentiment trend")
        if features["ticket_count"] > 10:
            factors.append("High support ticket volume")
        if features["days_since_contact"] > 60:
            factors.append("No contact in 60+ days")
        if features["renewal_days"] < 30:
            factors.append("Renewal due within 30 days")
        if features["avg_response_hrs"] > 48:
            factors.append("Slow support response times")
        if not factors:
            factors.append("Standard monitoring — no critical signals")
        return factors[:4]

    def _suggest_actions(self, risk_level: str, factors: List[str]) -> List[str]:
        """Map risk level to concrete next actions."""
        actions_map = {
            "critical": [
                "Immediately schedule executive escalation call",
                "Offer contract concession or service credit",
                "Assign dedicated CSM for daily check-ins",
                "Fast-track open support tickets",
            ],
            "high": [
                "Schedule QBR within next 2 weeks",
                "Send personalized check-in from account manager",
                "Review and resolve all open tickets",
                "Offer early renewal incentive",
            ],
            "medium": [
                "Schedule monthly business review",
                "Share product roadmap update",
                "Check in on open support items",
            ],
            "low": [
                "Continue standard engagement cadence",
                "Identify expansion opportunities",
            ],
        }
        return actions_map.get(risk_level, actions_map["medium"])