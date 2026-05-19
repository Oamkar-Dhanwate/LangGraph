# Analytics agent
"""
ClientIQ — Analytics Agent
Computes KPIs, revenue trends, engagement metrics, and
produces a business intelligence summary from CRM data.
"""

from typing import Any, Dict, List
from backend.graph.state import GraphState
from backend.services.mistral_client import MistralClient
from backend.utils.logger import logger
import json


class AnalyticsAgent:
    """
    Analytics Agent.

    Processes SQL results and retrieved data to compute:
    - Revenue metrics (MRR, ARR, pipeline value)
    - Client health distribution
    - Churn risk summary
    - Support ticket SLA metrics
    - Engagement trends
    """

    def __init__(self):
        self.llm = MistralClient()
        self.name = "analytics_agent"

    def run(self, state: GraphState) -> GraphState:
        """Compute analytics from available CRM data."""
        logger.info("[Analytics] Computing KPIs from {} SQL rows", len(state.get("sql_results", [])))

        sql_results = state.get("sql_results", [])
        analytics = state.get("analytics_data", {})

        if sql_results:
            # Revenue metrics
            analytics["revenue"] = self._compute_revenue(sql_results)

            # Health distribution
            analytics["health_distribution"] = self._health_distribution(sql_results)

            # Ticket SLA metrics
            analytics["ticket_metrics"] = self._ticket_metrics(sql_results)

            # Top/bottom clients
            analytics["top_clients"] = self._top_clients(sql_results)
            analytics["at_risk_clients"] = self._at_risk_clients(sql_results)

        # Generate KPI narrative using LLM
        kpi_summary = self._generate_kpi_summary(state["user_query"], analytics, sql_results)
        state["kpi_summary"] = kpi_summary
        state["analytics_data"] = analytics

        logger.info("[Analytics] KPI summary generated | {} metrics computed", len(analytics))

        state["agent_trace"].append(self.name)
        return state

    def _compute_revenue(self, rows: List[Dict]) -> Dict:
        """Extract revenue metrics from SQL rows."""
        revenues = [
            float(r.get("annual_revenue", 0) or r.get("value", 0) or r.get("amount", 0))
            for r in rows
            if r.get("annual_revenue") or r.get("value") or r.get("amount")
        ]
        if not revenues:
            return {}
        return {
            "total": sum(revenues),
            "average": sum(revenues) / len(revenues),
            "max": max(revenues),
            "min": min(revenues),
            "count": len(revenues),
        }

    def _health_distribution(self, rows: List[Dict]) -> Dict:
        """Bucket clients by health score."""
        scores = [float(r.get("health_score", 70)) for r in rows if r.get("health_score")]
        buckets = {"healthy": 0, "at_risk": 0, "critical": 0}
        for s in scores:
            if s >= 70:
                buckets["healthy"] += 1
            elif s >= 40:
                buckets["at_risk"] += 1
            else:
                buckets["critical"] += 1
        return buckets

    def _ticket_metrics(self, rows: List[Dict]) -> Dict:
        """Compute support SLA metrics."""
        response_times = [r.get("first_response_hrs") for r in rows if r.get("first_response_hrs")]
        resolution_times = [r.get("resolution_hrs") for r in rows if r.get("resolution_hrs")]

        def avg(lst):
            return sum(lst) / len(lst) if lst else None

        return {
            "avg_first_response_hrs": avg(response_times),
            "avg_resolution_hrs": avg(resolution_times),
            "open_tickets": sum(1 for r in rows if r.get("status") in ["open", "in_progress"]),
            "critical_tickets": sum(1 for r in rows if r.get("priority") == "critical"),
        }

    def _top_clients(self, rows: List[Dict], n: int = 5) -> List[Dict]:
        """Return top N clients by revenue or health score."""
        clients = [r for r in rows if r.get("name") or r.get("company_name")]
        return sorted(clients, key=lambda r: float(r.get("annual_revenue", 0) or 0), reverse=True)[:n]

    def _at_risk_clients(self, rows: List[Dict], threshold: float = 0.6) -> List[Dict]:
        """Return clients with churn risk above threshold."""
        return [
            r for r in rows
            if float(r.get("churn_risk", 0) or 0) >= threshold
        ]

    def _generate_kpi_summary(self, query: str, analytics: Dict, raw_rows: List) -> str:
        """Use LLM to narrate the computed analytics."""
        analytics_text = json.dumps(
            {k: v for k, v in analytics.items() if k != "sentiment_analysis"},
            indent=2, default=str
        )[:2000]

        prompt = f"""You are a business intelligence analyst. Generate a concise KPI summary.

User asked: {query}
Computed analytics:
{analytics_text}

Write a 3-5 sentence business intelligence summary with key metrics, trends, and red flags.
Use specific numbers. Do not repeat the raw JSON.

Summary:"""

        return self.llm.complete(prompt, temperature=0.3)
