# NetworkX graph service
"""
ClientIQ — Graph Service
Builds, persists, and queries the knowledge graph using NetworkX.
Exports Cytoscape.js-compatible JSON for frontend visualization.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from backend.database.models import Company, KGEntity, KGRelationship
from backend.utils.logger import logger

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False


class GraphService:
    """Manages the enterprise knowledge graph."""

    async def get_graph_data(
        self,
        db: AsyncSession,
        company_id: Optional[str] = None,
        limit: int = 200,
    ) -> Dict[str, List]:
        """
        Fetch graph data from TiDB and return in Cytoscape.js format.
        """
        entity_q = select(KGEntity).order_by(desc(KGEntity.created_at)).limit(limit)
        rel_q = select(KGRelationship).order_by(desc(KGRelationship.created_at)).limit(limit)

        entities_res = await db.execute(entity_q)
        rels_res = await db.execute(rel_q)

        entities = entities_res.scalars().all()
        rels = rels_res.scalars().all()

        entity_color_map = {
            "company":  "#3B8BD4",
            "contact":  "#1D9E75",
            "product":  "#EF9F27",
            "topic":    "#7F77DD",
            "risk":     "#E24B4A",
            "event":    "#D85A30",
        }

        nodes = [
            {
                "data": {
                    "id": e.id,
                    "label": e.name,
                    "type": e.entity_type,
                    "color": entity_color_map.get(e.entity_type, "#888"),
                    "size": 40 if e.entity_type == "company" else 25,
                    "properties": e.properties or {},
                }
            }
            for e in entities
        ]

        edges = [
            {
                "data": {
                    "id": r.id,
                    "source": r.source_entity,
                    "target": r.target_entity,
                    "label": r.relation_type,
                    "weight": float(r.weight),
                }
            }
            for r in rels
        ]

        return {"nodes": nodes, "edges": edges}

    async def upsert_entity(self, db: AsyncSession, entity_type: str, name: str, properties: dict = None, source_id: str = None) -> KGEntity:
        result = await db.execute(
            select(KGEntity).where(KGEntity.name == name, KGEntity.entity_type == entity_type)
        )
        entity = result.scalar_one_or_none()
        if not entity:
            entity = KGEntity(
                entity_type=entity_type,
                name=name,
                properties=properties or {},
                source_id=source_id,
            )
            db.add(entity)
            await db.flush()
        else:
            if source_id and not entity.source_id:
                entity.source_id = source_id
            if properties:
                entity.properties = {**(entity.properties or {}), **properties}
        return entity

    async def upsert_company(self, db: AsyncSession, company: Company) -> KGEntity:
        properties = {
            "company_id": company.id,
            "industry": company.industry,
            "size_category": company.size_category,
            "country": company.country,
            "account_tier": company.account_tier,
            "health_score": float(company.health_score) if company.health_score is not None else None,
            "churn_risk": float(company.churn_risk) if company.churn_risk is not None else None,
        }
        return await self.upsert_entity(
            db,
            entity_type="company",
            name=company.name,
            properties=properties,
            source_id=company.id,
        )

    async def upsert_relationship(
        self, db: AsyncSession,
        source_id: str, target_id: str,
        relation_type: str, weight: float = 1.0
    ) -> KGRelationship:
        result = await db.execute(
            select(KGRelationship).where(
                KGRelationship.source_entity == source_id,
                KGRelationship.target_entity == target_id,
                KGRelationship.relation_type == relation_type,
            )
        )
        rel = result.scalar_one_or_none()
        if not rel:
            rel = KGRelationship(
                source_entity=source_id,
                target_entity=target_id,
                relation_type=relation_type,
                weight=weight,
            )
            db.add(rel)
            await db.flush()
        return rel

    def analyze_centrality(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, float]:
        """Compute betweenness centrality scores (requires networkx)."""
        if not HAS_NX or not nodes:
            return {}
        G = nx.DiGraph()
        for n in nodes:
            G.add_node(n["data"]["id"], label=n["data"]["label"])
        for e in edges:
            G.add_edge(e["data"]["source"], e["data"]["target"])
        try:
            return nx.betweenness_centrality(G)
        except Exception:
            return {}


graph_service = GraphService()
