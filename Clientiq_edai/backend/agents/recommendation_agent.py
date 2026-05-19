# Recommendation agent
"""
ClientIQ — Recommendation Agent
Generates next-best-action recommendations and sales playbook suggestions
based on risk scores, sentiment, and client context.
"""

from typing import List, Dict
from backend.graph.state import GraphState
from backend.services.mistral_client import MistralClient
from backend.utils.logger import logger
import json


class RecommendationAgent:
    """
    Recommendation Agent.

    Produces:
    - Ranked next-best-actions per client
    - Sales opportunity triggers
    - Product recommendations
    - Communication strategy suggestions
    """

    def __init__(self):
        self.llm = MistralClient()
        self.name = "recommendation_agent"

    def run(self, state: GraphState) -> GraphState:
        """Generate recommendations from risk scores and context."""
        logger.info("[Recommendations] Generating recommendations")

        risk_scores = state.get("risk_scores", [])
        recommendations: List[str] = []
        next_best_actions: List[Dict[str, str]] = []

        # Pull recommendations from risk agent
        for risk in risk_scores[:5]:
            for action in risk.get("recommended_actions", []):
                action_item = {
                    "company": risk["company_name"],
                    "action": action,
                    "priority": risk["risk_level"],
                    "reason": f"Churn probability: {risk['churn_probability']:.0%}",
                }
                next_best_actions.append(action_item)

        # Use LLM for strategic recommendations
        llm_recs = self._generate_llm_recommendations(state)
        recommendations = llm_recs

        state["recommendations"] = recommendations
        state["next_best_actions"] = next_best_actions[:10]
        state["agent_trace"].append(self.name)

        logger.info("[Recommendations] {} recommendations | {} next actions", len(recommendations), len(next_best_actions))
        return state

    def _generate_llm_recommendations(self, state: GraphState) -> List[str]:
        """Use LLM to generate contextual strategic recommendations."""
        context = {
            "query": state["user_query"],
            "intent": state.get("intent"),
            "risk_clients": [
                {"name": r["company_name"], "risk": r["risk_level"]}
                for r in state.get("risk_scores", [])[:5]
            ],
            "sentiment": state.get("sentiment_label"),
            "analytics": {k: v for k, v in state.get("analytics_data", {}).items() if k != "sentiment_analysis"},
        }

        prompt = f"""You are a senior sales strategist and customer success expert.
Based on the client intelligence data below, provide 5 specific, actionable recommendations.

Context:
{json.dumps(context, indent=2, default=str)[:1500]}

Retrieved context summary:
{state.get('fused_context', '')[:500]}

Generate 5 recommendations as a numbered list. Each should be:
- Specific and actionable (not generic)
- Business-outcome focused
- Time-bound where possible

Recommendations:"""

        response = self.llm.complete(prompt, temperature=0.4)

        # Parse numbered list
        lines = response.strip().split("\n")
        recs = []
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("•") or line.startswith("-")):
                cleaned = line.lstrip("0123456789.-•) ").strip()
                if len(cleaned) > 20:
                    recs.append(cleaned)
        return recs[:5] if recs else [response.strip()]
