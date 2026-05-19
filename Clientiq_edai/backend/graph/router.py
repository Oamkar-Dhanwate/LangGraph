# Conditional edges router
"""
ClientIQ — LangGraph Router
Implements conditional edge routing between agents based on state and intent.
"""

from typing import List
from backend.graph.state import GraphState
from backend.utils.logger import logger

# ─── Intent → Agent mapping ──────────────────────────────────────────────────

INTENT_AGENT_MAP = {
    "crm_query":        ["compliance_agent", "crm_sql_agent", "analytics_agent", "citation_agent"],
    "document_search":  ["compliance_agent", "retrieval_agent", "citation_agent"],
    "sentiment_check":  ["compliance_agent", "retrieval_agent", "sentiment_agent", "citation_agent"],
    "risk_analysis":    ["compliance_agent", "crm_sql_agent", "retrieval_agent", "risk_agent", "recommendation_agent", "citation_agent"],
    "recommendation":   ["compliance_agent", "crm_sql_agent", "retrieval_agent", "risk_agent", "recommendation_agent", "citation_agent"],
    "analytics":        ["compliance_agent", "crm_sql_agent", "analytics_agent", "citation_agent"],
    "knowledge_graph":  ["compliance_agent", "crm_sql_agent", "retrieval_agent", "knowledge_graph_agent", "citation_agent"],
    "general_qa":       ["compliance_agent", "retrieval_agent", "citation_agent"],
    "conversation":     ["memory_agent", "retrieval_agent", "citation_agent"],
}


def classify_intent(query: str) -> str:
    """
    Rule-based intent classifier.
    In production, replace with an LLM call for better accuracy.
    """
    query_lower = query.lower()

    intent_keywords = {
        "crm_query":       ["client", "account", "company", "revenue", "contact", "deal", "pipeline", "opportunity"],
        "sentiment_check": ["sentiment", "feeling", "emotion", "happy", "unhappy", "satisfaction", "dissatisfied", "churn signal"],
        "risk_analysis":   ["churn", "risk", "at risk", "renewal", "cancel", "losing", "attrition", "expir"],
        "recommendation":  ["recommend", "suggest", "next step", "action", "what should", "strategy", "improve"],
        "analytics":       ["analytics", "trend", "kpi", "metric", "performance", "report", "dashboard", "revenue trend"],
        "knowledge_graph": ["knowledge graph", "relationship", "entity", "connection", "network", "linked"],
        "document_search": ["document", "email", "meeting", "transcript", "contract", "ticket", "notes", "call"],
        "general_qa":      ["what is", "explain", "how does", "tell me about", "describe"],
    }

    for intent, keywords in intent_keywords.items():
        if any(kw in query_lower for kw in keywords):
            logger.debug("Intent classified as '{}' for query: {}", intent, query[:60])
            return intent

    return "general_qa"


def route_after_supervisor(state: GraphState) -> str:
    """
    Primary router called after Supervisor agent.
    Returns the name of the next node to execute.
    """
    if not state.get("compliance_cleared", True):
        return "end"
    if state.get("errors"):
        return "end"

    required = state.get("required_agents", [])
    if not required:
        return "end"

    # Always start with compliance check
    if "compliance_agent" in required:
        return "compliance_agent"

    return required[0]


def route_after_compliance(state: GraphState) -> str:
    """Route after compliance check passes or blocks."""
    if not state.get("compliance_cleared", True):
        logger.warning("Query blocked by compliance agent | flags={}", state.get("compliance_flags"))
        return "end"

    required = state.get("required_agents", [])
    # Remove compliance from list, get next
    remaining = [a for a in required if a != "compliance_agent"]
    if not remaining:
        return "end"
    return remaining[0]


def route_after_crm_sql(state: GraphState) -> str:
    """Route after CRM SQL agent executes."""
    required = state.get("required_agents", [])
    executed = state.get("agent_trace", [])

    # Find agents not yet executed (excluding compliance + crm_sql itself)
    skip = {"compliance_agent", "crm_sql_agent"}
    pending = [a for a in required if a not in skip and a not in executed]

    if not pending:
        return "citation_agent"
    return pending[0]


def route_after_retrieval(state: GraphState) -> str:
    """Route after vector retrieval agent."""
    required = state.get("required_agents", [])
    executed = set(state.get("agent_trace", []))

    skip = {"compliance_agent", "crm_sql_agent", "retrieval_agent"}
    pending = [a for a in required if a not in skip and a not in executed]

    if not pending:
        return "citation_agent"
    return pending[0]


def route_to_final(state: GraphState) -> str:
    """Final routing — always go to supervisor for response synthesis."""
    return "supervisor"


def get_required_agents(intent: str) -> List[str]:
    """Return ordered list of required agents for a given intent."""
    return INTENT_AGENT_MAP.get(intent, INTENT_AGENT_MAP["general_qa"])