# Knowledge graph routes
"""
ClientIQ — Knowledge Graph Routes
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.database.connection import get_db
from backend.services.graph_service import graph_service
from backend.api.routes_auth import get_current_user

router = APIRouter()


@router.get("/")
async def get_graph(
    company_id: Optional[str] = None,
    limit: int = Query(200, le=500),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return Cytoscape.js-compatible knowledge graph data."""
    data = await graph_service.get_graph_data(db, company_id=company_id, limit=limit)
    return data


@router.get("/centrality")
async def graph_centrality(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return betweenness centrality scores for all nodes."""
    data = await graph_service.get_graph_data(db, limit=200)
    centrality = graph_service.analyze_centrality(data["nodes"], data["edges"])
    return {"centrality": centrality}