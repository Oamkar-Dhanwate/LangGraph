# Knowledge graph agent
"""
ClientIQ — Knowledge Graph Agent
Extracts entities and relationships from retrieved text,
builds a NetworkX graph, and returns Cytoscape.js-compatible data.
"""

import re
from typing import Any, Dict, List, Set, Tuple
from backend.graph.state import GraphState
from backend.services.mistral_client import MistralClient
from backend.utils.helpers import generate_id
from backend.utils.logger import logger

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False


# Entity type color mapping for Cytoscape.js
ENTITY_COLORS = {
    "company":  "#3B8BD4",
    "contact":  "#1D9E75",
    "product":  "#EF9F27",
    "topic":    "#7F77DD",
    "risk":     "#E24B4A",
    "event":    "#D85A30",
}


class KnowledgeGraphAgent:
    """
    Knowledge Graph Agent.

    1. Uses LLM to extract (entity, relation, entity) triples from text
    2. Builds a NetworkX graph
    3. Converts to Cytoscape.js format for frontend visualization
    """

    def __init__(self):
        self.llm = MistralClient()
        self.name = "knowledge_graph_agent"

    def run(self, state: GraphState) -> GraphState:
        """Extract entities, build graph, output Cytoscape format."""
        logger.info("[KnowledgeGraph] Extracting entities from context")

        text = state.get("fused_context", "") or state.get("user_query", "")
        if not text:
            state["agent_trace"].append(self.name)
            return state

        # Extract triples via LLM
        triples = self._extract_triples(text[:2000])

        # Build graph
        nodes, edges = self._build_cytoscape_data(triples, state)

        state["kg_nodes"] = nodes
        state["kg_edges"] = edges
        state["agent_trace"].append(self.name)

        logger.info("[KnowledgeGraph] {} nodes | {} edges extracted", len(nodes), len(edges))
        return state

    def _extract_triples(self, text: str) -> List[Tuple[str, str, str, str, str]]:
        """
        Use LLM to extract (subject, subject_type, relation, object, object_type) triples.
        Returns list of 5-tuples.
        """
        prompt = f"""Extract knowledge graph triples from the text below.
Format each triple as: SUBJECT_TYPE|SUBJECT|RELATION|OBJECT|OBJECT_TYPE

Entity types: company, contact, product, topic, risk, event
Relations: contracted_with, escalated_to, attended, owns, discussed, at_risk_of, related_to, reported_by

Extract up to 15 triples. Output ONLY the triples, one per line.

Text:
{text}

Triples:"""

        response = self.llm.complete(prompt, temperature=0.1)

        triples = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if "|" in line:
                parts = line.split("|")
                if len(parts) == 5:
                    s_type, subject, relation, obj, o_type = [p.strip() for p in parts]
                    if subject and relation and obj:
                        triples.append((subject, s_type, relation, obj, o_type))
        return triples

    def _build_cytoscape_data(
        self,
        triples: List[Tuple],
        state: GraphState,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Convert triples to Cytoscape.js nodes and edges."""
        node_map: Dict[str, Dict] = {}
        edges: List[Dict] = []

        # Add company from context
        entity_context = state.get("entity_context", {})
        if entity_context.get("company_name"):
            cn = entity_context["company_name"]
            node_map[cn] = {
                "data": {
                    "id": generate_id("node"),
                    "label": cn,
                    "type": "company",
                    "color": ENTITY_COLORS["company"],
                    "size": 40,
                }
            }

        for subject, s_type, relation, obj, o_type in triples:
            s_type = s_type if s_type in ENTITY_COLORS else "topic"
            o_type = o_type if o_type in ENTITY_COLORS else "topic"

            # Add/update source node
            if subject not in node_map:
                node_map[subject] = {
                    "data": {
                        "id": generate_id("node"),
                        "label": subject[:40],
                        "type": s_type,
                        "color": ENTITY_COLORS.get(s_type, "#888"),
                        "size": 30 if s_type == "company" else 20,
                    }
                }

            # Add/update target node
            if obj not in node_map:
                node_map[obj] = {
                    "data": {
                        "id": generate_id("node"),
                        "label": obj[:40],
                        "type": o_type,
                        "color": ENTITY_COLORS.get(o_type, "#888"),
                        "size": 20,
                    }
                }

            source_id = node_map[subject]["data"]["id"]
            target_id = node_map[obj]["data"]["id"]

            edges.append({
                "data": {
                    "id": generate_id("edge"),
                    "source": source_id,
                    "target": target_id,
                    "label": relation,
                }
            })

        return list(node_map.values()), edges
