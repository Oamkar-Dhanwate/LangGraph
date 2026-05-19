# State definitions
"""
ClientIQ — LangGraph Shared State
Defines the TypedDict that flows through the entire multi-agent graph.
Every agent reads from and writes into this shared state object.
"""

from typing import Any, Dict, List, Optional, TypedDict


class AgentMessage(TypedDict):
    """A single message in the conversation history."""
    role: str          # "user" | "assistant" | "system" | "tool"
    content: str
    agent: Optional[str]    # which agent produced this
    timestamp: str


class RetrievedChunk(TypedDict):
    """A single RAG retrieval result."""
    chunk_id: str
    source: str
    source_type: str   # "email" | "meeting" | "call" | "contract" | "ticket"
    company_id: str
    text: str
    score: float


class Citation(TypedDict):
    """Source citation for a generated response."""
    source: str
    chunk_id: str
    score: float
    excerpt: str


class RiskScore(TypedDict):
    """Churn / renewal risk assessment."""
    company_id: str
    company_name: str
    churn_probability: float   # 0.0 – 1.0
    risk_level: str            # "low" | "medium" | "high" | "critical"
    key_factors: List[str]
    recommended_actions: List[str]


class GraphState(TypedDict):
    """
    Master shared state object passed through the LangGraph workflow.
    Each field is updated by one or more agents.
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    user_query: str
    session_id: str
    user_id: str
    user_role: str                     # RBAC role name

    # ── Routing ───────────────────────────────────────────────────────────────
    intent: str                        # classified intent
    required_agents: List[str]         # which agents to invoke
    current_agent: str                 # currently executing agent
    routing_metadata: Dict[str, Any]

    # ── SQL / CRM Results ─────────────────────────────────────────────────────
    sql_query: str
    sql_results: List[Dict[str, Any]]
    sql_error: Optional[str]

    # ── Vector / RAG Results ──────────────────────────────────────────────────
    retrieved_chunks: List[RetrievedChunk]
    fused_context: str                 # merged SQL + vector context

    # ── Citations ─────────────────────────────────────────────────────────────
    citations: List[Citation]
    confidence_score: float

    # ── Sentiment ─────────────────────────────────────────────────────────────
    sentiment_score: float             # -1.0 to 1.0
    sentiment_label: str              # positive/neutral/negative
    emotion_signals: List[str]         # detected emotion keywords

    # ── Analytics ─────────────────────────────────────────────────────────────
    analytics_data: Dict[str, Any]
    kpi_summary: str

    # ── Risk & Recommendations ────────────────────────────────────────────────
    risk_scores: List[RiskScore]
    recommendations: List[str]
    next_best_actions: List[Dict[str, str]]

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    kg_nodes: List[Dict[str, Any]]
    kg_edges: List[Dict[str, Any]]

    # ── Memory / Conversation ─────────────────────────────────────────────────
    conversation_history: List[AgentMessage]
    entity_context: Dict[str, Any]    # current company/contact in focus
    memory_summary: str               # compressed prior context

    # ── Compliance ────────────────────────────────────────────────────────────
    compliance_cleared: bool
    compliance_flags: List[str]
    redacted_fields: List[str]

    # ── Final Output ──────────────────────────────────────────────────────────
    final_response: str
    response_metadata: Dict[str, Any]
    agent_trace: List[str]             # execution order log
    errors: List[str]
    completed: bool