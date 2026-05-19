# Workflow definitions
"""
ClientIQ — LangGraph Multi-Agent Workflow
Builds and compiles the full StateGraph with all 11 agents,
conditional routing, and stateful execution.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from backend.graph.state import GraphState
from backend.graph.router import (
    classify_intent,
    get_required_agents,
    route_after_compliance,
    route_after_crm_sql,
    route_after_retrieval,
    route_to_final,
)
from backend.agents.supervisor import SupervisorAgent
from backend.agents.compliance_agent import ComplianceAgent
from backend.agents.crm_sql_agent import CRMSQLAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.citation_agent import CitationAgent
from backend.agents.memory_agent import MemoryAgent
from backend.agents.sentiment_agent import SentimentAgent
from backend.agents.analytics_agent import AnalyticsAgent
from backend.agents.risk_agent import RiskAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.knowledge_graph_agent import KnowledgeGraphAgent
from backend.utils.logger import logger


# ─── Instantiate all agents ───────────────────────────────────────────────────

supervisor_agent    = SupervisorAgent()
compliance_agent    = ComplianceAgent()
crm_sql_agent       = CRMSQLAgent()
retrieval_agent     = RetrievalAgent()
citation_agent      = CitationAgent()
memory_agent        = MemoryAgent()
sentiment_agent     = SentimentAgent()
analytics_agent     = AnalyticsAgent()
risk_agent          = RiskAgent()
recommendation_agent = RecommendationAgent()
kg_agent            = KnowledgeGraphAgent()


# ─── Node wrapper functions ────────────────────────────────────────────────────

def run_supervisor(state: GraphState) -> GraphState:
    return supervisor_agent.run(state)

def run_compliance(state: GraphState) -> GraphState:
    return compliance_agent.run(state)

def run_crm_sql(state: GraphState) -> GraphState:
    return crm_sql_agent.run(state)

def run_retrieval(state: GraphState) -> GraphState:
    return retrieval_agent.run(state)

def run_citation(state: GraphState) -> GraphState:
    return citation_agent.run(state)

def run_memory(state: GraphState) -> GraphState:
    return memory_agent.run(state)

def run_sentiment(state: GraphState) -> GraphState:
    return sentiment_agent.run(state)

def run_analytics(state: GraphState) -> GraphState:
    return analytics_agent.run(state)

def run_risk(state: GraphState) -> GraphState:
    return risk_agent.run(state)

def run_recommendation(state: GraphState) -> GraphState:
    return recommendation_agent.run(state)

def run_knowledge_graph(state: GraphState) -> GraphState:
    return kg_agent.run(state)

def run_final_synthesis(state: GraphState) -> GraphState:
    """Final synthesis pass — supervisor composes the ultimate response."""
    return supervisor_agent.synthesize(state)


# ─── Route decision functions ──────────────────────────────────────────────────

def should_continue_after_compliance(state: GraphState) -> str:
    return route_after_compliance(state)

def should_continue_after_crm(state: GraphState) -> str:
    return route_after_crm_sql(state)

def should_continue_after_retrieval(state: GraphState) -> str:
    return route_after_retrieval(state)

def should_finalize(state: GraphState) -> str:
    return "final_synthesis" if not state.get("errors") else END


# ─── Build the graph ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construct the full LangGraph StateGraph.

    Flow:
      [supervisor]
          ↓
      [compliance_agent] — blocked → [END]
          ↓ cleared
      [crm_sql_agent] ─────────────────────────────────────────┐
      [retrieval_agent] ─────────────────────────────────────  │
      [memory_agent]     (parallel where possible)             │
          ↓                                                     │
      [sentiment_agent]                                         │
      [analytics_agent]                                         │
      [risk_agent]                                              │
      [recommendation_agent]                                    │
      [knowledge_graph_agent]                                   │
          ↓                                                     │
      [citation_agent] ←───────────────────────────────────────┘
          ↓
      [final_synthesis / supervisor]
          ↓
      [END]
    """

    graph = StateGraph(GraphState)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("supervisor",          run_supervisor)
    graph.add_node("compliance_agent",    run_compliance)
    graph.add_node("crm_sql_agent",       run_crm_sql)
    graph.add_node("retrieval_agent",     run_retrieval)
    graph.add_node("citation_agent",      run_citation)
    graph.add_node("memory_agent",        run_memory)
    graph.add_node("sentiment_agent",     run_sentiment)
    graph.add_node("analytics_agent",     run_analytics)
    graph.add_node("risk_agent",          run_risk)
    graph.add_node("recommendation_agent", run_recommendation)
    graph.add_node("knowledge_graph_agent", run_knowledge_graph)
    graph.add_node("final_synthesis",     run_final_synthesis)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("supervisor")

    # ── Edges from supervisor → compliance ────────────────────────────────────
    graph.add_edge("supervisor", "compliance_agent")

    # ── Conditional: compliance → next agent or END ───────────────────────────
    graph.add_conditional_edges(
        "compliance_agent",
        should_continue_after_compliance,
        {
            "crm_sql_agent":         "crm_sql_agent",
            "retrieval_agent":       "retrieval_agent",
            "memory_agent":          "memory_agent",
            "sentiment_agent":       "sentiment_agent",
            "analytics_agent":       "analytics_agent",
            "risk_agent":            "risk_agent",
            "recommendation_agent":  "recommendation_agent",
            "knowledge_graph_agent": "knowledge_graph_agent",
            "citation_agent":        "citation_agent",
            "end":                   END,
        },
    )

    # ── CRM SQL → conditional next ────────────────────────────────────────────
    graph.add_conditional_edges(
        "crm_sql_agent",
        should_continue_after_crm,
        {
            "retrieval_agent":       "retrieval_agent",
            "sentiment_agent":       "sentiment_agent",
            "analytics_agent":       "analytics_agent",
            "risk_agent":            "risk_agent",
            "recommendation_agent":  "recommendation_agent",
            "knowledge_graph_agent": "knowledge_graph_agent",
            "citation_agent":        "citation_agent",
        },
    )

    # ── Retrieval → conditional next ──────────────────────────────────────────
    graph.add_conditional_edges(
        "retrieval_agent",
        should_continue_after_retrieval,
        {
            "sentiment_agent":       "sentiment_agent",
            "analytics_agent":       "analytics_agent",
            "risk_agent":            "risk_agent",
            "recommendation_agent":  "recommendation_agent",
            "knowledge_graph_agent": "knowledge_graph_agent",
            "citation_agent":        "citation_agent",
        },
    )

    # ── Simple sequential edges ────────────────────────────────────────────────
    graph.add_edge("memory_agent",          "retrieval_agent")
    graph.add_edge("sentiment_agent",       "citation_agent")
    graph.add_edge("analytics_agent",       "citation_agent")
    graph.add_edge("risk_agent",            "recommendation_agent")
    graph.add_edge("recommendation_agent",  "citation_agent")
    graph.add_edge("knowledge_graph_agent", "citation_agent")

    # ── Citation → final synthesis ─────────────────────────────────────────────
    graph.add_edge("citation_agent", "final_synthesis")

    # ── Final → END ───────────────────────────────────────────────────────────
    graph.add_edge("final_synthesis", END)

    return graph


# ── Compiled graph (module-level singleton) ────────────────────────────────────
_compiled_graph = None


def get_compiled_graph():
    """Return compiled LangGraph (lazy singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        g = build_graph()
        _compiled_graph = g.compile()
        logger.info("LangGraph workflow compiled successfully")
    return _compiled_graph


async def execute_query(
    user_query: str,
    session_id: str,
    user_id: str,
    user_role: str = "analyst",
    conversation_history: list = None,
    entity_context: dict = None,
) -> Dict[str, Any]:
    """
    Main entry point: execute a user query through the full agent pipeline.

    Returns the final state after all agents have executed.
    """
    from backend.graph.router import classify_intent, get_required_agents

    intent = classify_intent(user_query)
    required_agents = get_required_agents(intent)

    initial_state: GraphState = {
        # Input
        "user_query":           user_query,
        "session_id":           session_id,
        "user_id":              user_id,
        "user_role":            user_role,

        # Routing
        "intent":               intent,
        "required_agents":      required_agents,
        "current_agent":        "",
        "routing_metadata":     {"classified_at": datetime.now(timezone.utc).isoformat()},

        # SQL
        "sql_query":            "",
        "sql_results":          [],
        "sql_error":            None,

        # RAG
        "retrieved_chunks":     [],
        "fused_context":        "",

        # Citations
        "citations":            [],
        "confidence_score":     0.0,

        # Sentiment
        "sentiment_score":      0.0,
        "sentiment_label":      "neutral",
        "emotion_signals":      [],

        # Analytics
        "analytics_data":       {},
        "kpi_summary":          "",

        # Risk
        "risk_scores":          [],
        "recommendations":      [],
        "next_best_actions":    [],

        # KG
        "kg_nodes":             [],
        "kg_edges":             [],

        # Memory
        "conversation_history": conversation_history or [],
        "entity_context":       entity_context or {},
        "memory_summary":       "",

        # Compliance
        "compliance_cleared":   True,
        "compliance_flags":     [],
        "redacted_fields":      [],

        # Output
        "final_response":       "",
        "response_metadata":    {},
        "agent_trace":          [],
        "errors":               [],
        "completed":            False,
    }

    logger.info(
        "Executing query | intent={} | agents={} | session={}",
        intent, required_agents, session_id
    )

    graph = get_compiled_graph()
    final_state = await graph.ainvoke(initial_state)

    logger.info(
        "Query completed | trace={} | response_len={}",
        final_state.get("agent_trace"),
        len(final_state.get("final_response", ""))
    )

    return final_state