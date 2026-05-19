# Query routes
"""
ClientIQ — Query Routes
Main endpoint for executing AI queries through the LangGraph agent pipeline.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.database.connection import get_db
from backend.api.routes_auth import get_current_user
from backend.services.audit_service import audit_service
from backend.utils.logger import logger

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None

class Citation(BaseModel):
    source: str
    chunk_id: str
    score: float
    excerpt: str

class QueryResponse(BaseModel):
    response: str
    session_id: str
    intent: str
    confidence: float
    citations: List[Dict]
    agents_used: List[str]
    sentiment: Optional[str] = None
    risk_scores: Optional[List[Dict]] = None
    recommendations: Optional[List[str]] = None
    analytics: Optional[Dict] = None
    kg_nodes: Optional[List[Dict]] = None
    kg_edges: Optional[List[Dict]] = None


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=QueryResponse)
async def execute_query(
    body: QueryRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a natural language query through the full multi-agent pipeline.

    This endpoint:
    1. Routes through LangGraph (11 agents)
    2. Performs hybrid RAG retrieval
    3. Returns structured response with citations
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = body.session_id or str(uuid.uuid4())

    # Build entity context
    entity_context: Dict[str, Any] = {}
    if body.company_id:
        entity_context["company_id"] = body.company_id
    if body.company_name:
        entity_context["company_name"] = body.company_name

    # Get user role
    from sqlalchemy import select
    from backend.database.models import Role
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalar_one_or_none()
    user_role = role.name if role else "viewer"

    logger.info("[QueryAPI] user={} role={} query={}", current_user.id, user_role, body.query[:60])

    try:
        from backend.graph.workflow import execute_query as run_graph
        final_state = await run_graph(
            user_query=body.query,
            session_id=session_id,
            user_id=current_user.id,
            user_role=user_role,
            entity_context=entity_context,
        )
    except Exception as e:
        logger.error("[QueryAPI] Graph execution failed: {}", e)
        await audit_service.log(db, current_user.id, "query_failed",
                                details={"query": body.query, "error": str(e)}, status="failure")
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")

    # Audit log
    await audit_service.log(
        db, current_user.id, "query_executed",
        details={"query": body.query, "intent": final_state.get("intent"), "session_id": session_id},
        ip_address=request.client.host if request.client else None,
    )

    return QueryResponse(
        response=final_state.get("final_response", "No response generated."),
        session_id=session_id,
        intent=final_state.get("intent", "general_qa"),
        confidence=final_state.get("confidence_score", 0.0),
        citations=final_state.get("citations", []),
        agents_used=final_state.get("agent_trace", []),
        sentiment=final_state.get("sentiment_label"),
        risk_scores=final_state.get("risk_scores", [])[:5],
        recommendations=final_state.get("recommendations", []),
        analytics=final_state.get("analytics_data"),
        kg_nodes=final_state.get("kg_nodes"),
        kg_edges=final_state.get("kg_edges"),
    )


@router.get("/intents")
async def list_intents():
    """Return all supported query intents."""
    from backend.graph.router import INTENT_AGENT_MAP
    return {
        "intents": [
            {"intent": k, "agents": v}
            for k, v in INTENT_AGENT_MAP.items()
        ]
    }