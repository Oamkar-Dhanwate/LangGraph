# Supervisor agent
"""
ClientIQ — Supervisor Agent
Orchestrates the multi-agent workflow:
  1. Plans which agents are needed for a given query
  2. Synthesizes the final response from all agent outputs
"""

from datetime import datetime, timezone
from backend.graph.state import GraphState
from backend.services.mistral_client import MistralClient
from backend.graph.router import classify_intent, get_required_agents
from backend.utils.logger import logger


class SupervisorAgent:
    """
    The Supervisor Agent acts as the central orchestrator.
    It classifies user intent, assembles required agents, and
    synthesizes a final coherent response from all agent outputs.
    """

    def __init__(self):
        self.llm = MistralClient()
        self.name = "supervisor"

    def run(self, state: GraphState) -> GraphState:
        """
        Phase 1 — Query planning.
        Classify intent and determine which agents are needed.
        """
        logger.info("[Supervisor] Planning query: {}", state["user_query"][:80])

        intent = classify_intent(state["user_query"])
        required_agents = get_required_agents(intent)

        state["intent"] = intent
        state["required_agents"] = required_agents
        state["current_agent"] = self.name
        state["agent_trace"].append(self.name)

        logger.info("[Supervisor] Intent={} | Agents={}", intent, required_agents)
        return state

    def synthesize(self, state: GraphState) -> GraphState:
        """
        Phase 2 — Final response synthesis.
        Combines all agent outputs into a single coherent response.
        """
        logger.info("[Supervisor] Synthesizing final response")

        # Build synthesis context
        context_parts = []

        if state.get("fused_context"):
            context_parts.append(f"RETRIEVED CONTEXT:\n{state['fused_context']}")

        if state.get("sql_results"):
            import json
            context_parts.append(f"CRM DATA:\n{json.dumps(state['sql_results'][:5], indent=2)}")

        if state.get("kpi_summary"):
            context_parts.append(f"ANALYTICS:\n{state['kpi_summary']}")

        if state.get("risk_scores"):
            risk_text = "\n".join(
                f"- {r['company_name']}: {r['risk_level']} churn risk ({r['churn_probability']:.1%})"
                for r in state["risk_scores"]
            )
            context_parts.append(f"RISK ANALYSIS:\n{risk_text}")

        if state.get("recommendations"):
            rec_text = "\n".join(f"• {r}" for r in state["recommendations"][:5])
            context_parts.append(f"RECOMMENDATIONS:\n{rec_text}")

        if state.get("sentiment_label"):
            context_parts.append(
                f"SENTIMENT: {state['sentiment_label']} (score: {state.get('sentiment_score', 0):.2f})"
            )

        if state.get("memory_summary"):
            context_parts.append(f"CONVERSATION CONTEXT:\n{state['memory_summary']}")

        full_context = "\n\n---\n\n".join(context_parts) if context_parts else "No additional context retrieved."

        system_prompt = """You are ClientIQ, an enterprise AI intelligence platform for sales and client teams.
You synthesize information from multiple specialized AI agents to provide clear, actionable business insights.

Guidelines:
- Be concise but comprehensive
- Lead with the most important insight
- Use bullet points for lists
- Always ground claims in the provided data
- Mention confidence level when uncertain
- Reference citations when available
- Suggest next actions when relevant"""

        user_prompt = f"""User Question: {state['user_query']}

Agent Outputs:
{full_context}

Citations available: {len(state.get('citations', []))}
Compliance cleared: {state.get('compliance_cleared', True)}

Provide a comprehensive, data-grounded response:"""

        response = self.llm.chat(
            system=system_prompt,
            user=user_prompt,
            temperature=0.3,
        )

        state["final_response"] = response
        state["completed"] = True
        state["agent_trace"].append("final_synthesis")
        state["response_metadata"] = {
            "intent": state.get("intent"),
            "agents_used": state.get("agent_trace", []),
            "citation_count": len(state.get("citations", [])),
            "confidence": state.get("confidence_score", 0.0),
            "synthesized_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("[Supervisor] Response synthesized | {} chars", len(response))
        return state
