# Knowledge graph generation
"""
ClientIQ — Knowledge Graph Data Generator
Extracts entities from CRM records and builds a rich
entity-relationship graph ready for Cytoscape.js visualization.
"""

import random
from typing import Any, Dict, List, Tuple
from faker import Faker

fake = Faker()
random.seed(42)

# ── Entity type definitions ───────────────────────────────────────────────────

ENTITY_TYPES = ["company", "contact", "product", "topic", "event", "risk"]

PRODUCTS = [
    "Analytics Suite Pro", "AI Platform Enterprise", "Data Connector API",
    "Security Gateway", "Compliance Module", "Reporting Dashboard",
    "Integration Hub", "Customer 360 View", "Real-time Alerts",
]

TOPICS = [
    "contract renewal", "support escalation", "API integration",
    "pricing negotiation", "product roadmap", "data migration",
    "executive alignment", "churn risk", "expansion opportunity",
    "onboarding", "compliance audit", "SLA review", "security concern",
    "performance issue", "budget approval",
]

EVENTS = [
    "Annual QBR", "Product Launch Webinar", "Executive Briefing",
    "Technical Workshop", "Renewal Meeting", "Escalation Call",
    "Onboarding Kickoff", "Health Check Review",
]

RISKS = [
    "Late renewal risk", "Budget freeze", "Champion leaving",
    "Competitive evaluation", "Data compliance issue",
    "Integration blocker", "Performance SLA breach",
]

# ── Relationship type definitions ─────────────────────────────────────────────

RELATIONS = {
    ("company",  "topic"):   ["discussed", "raised_concern_about", "interested_in"],
    ("company",  "product"): ["contracted_with", "evaluating", "uses"],
    ("company",  "event"):   ["attended", "hosted", "invited_to"],
    ("company",  "risk"):    ["at_risk_of", "flagged_for", "experiencing"],
    ("contact",  "company"): ["works_at", "champions", "manages"],
    ("contact",  "topic"):   ["raised", "concerned_about", "owns"],
    ("contact",  "event"):   ["attended", "presented_at"],
    ("product",  "topic"):   ["related_to", "addresses", "lacks_feature_for"],
    ("topic",    "risk"):    ["escalates_to", "signals"],
    ("event",    "topic"):   ["covered", "resulted_in_action_on"],
}


def _pick_relation(src_type: str, tgt_type: str) -> str:
    key = (src_type, tgt_type)
    return random.choice(RELATIONS.get(key, ["related_to"]))


# ── Entity generation ─────────────────────────────────────────────────────────

def generate_entities(
    companies: List[Dict],
    contacts: List[Dict] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate KG entities and relationships from CRM data.

    Returns:
        (entities, relationships) — lists of dicts for DB insertion
    """
    entities: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []

    # Track created entities by name to avoid duplicates
    entity_index: Dict[str, str] = {}   # name → id (temp counter-based)

    def make_entity(
        entity_type: str,
        name: str,
        properties: Dict = None,
        source_id: str = None,
    ) -> str:
        """Create entity if not exists, return its temp key."""
        key = f"{entity_type}::{name}"
        if key not in entity_index:
            eid = f"E{len(entity_index)+1:06d}"
            entity_index[key] = eid
            entities.append({
                "id":          eid,
                "entity_type": entity_type,
                "name":        name[:200],
                "properties":  properties or {},
                "source_id":   source_id,
            })
        return entity_index[key]

    def make_relation(src_id: str, tgt_id: str, relation: str, weight: float = 1.0):
        relationships.append({
            "source_entity": src_id,
            "target_entity": tgt_id,
            "relation_type": relation,
            "weight":        round(weight, 2),
            "properties":    {},
        })

    # Build shared pool of products, topics, events, risks
    product_ids = [
        make_entity("product", p)
        for p in random.sample(PRODUCTS, k=min(len(PRODUCTS), 8))
    ]
    topic_ids = [
        make_entity("topic", t)
        for t in random.sample(TOPICS, k=min(len(TOPICS), 10))
    ]
    event_ids = [
        make_entity("event", e)
        for e in random.sample(EVENTS, k=min(len(EVENTS), 5))
    ]
    risk_ids = [
        make_entity("risk", r)
        for r in random.sample(RISKS, k=min(len(RISKS), 5))
    ]

    # Link shared entities among themselves
    for t_id in topic_ids:
        for r_id in random.sample(risk_ids, k=1):
            make_relation(t_id, r_id, "escalates_to", weight=round(random.uniform(0.3, 1.0), 2))
    for e_id in event_ids:
        for t_id in random.sample(topic_ids, k=2):
            make_relation(e_id, t_id, "covered", weight=1.0)

    # Companies → their entities
    for company in companies:
        cid   = company.get("id", "")
        cname = company.get("name", "Unknown")
        c_eid = make_entity("company", cname, properties={"industry": company.get("industry"), "tier": company.get("account_tier")}, source_id=cid)

        # Company → topics (2–4)
        for t_id in random.sample(topic_ids, k=min(4, len(topic_ids))):
            make_relation(c_eid, t_id, "discussed", weight=round(random.uniform(0.4, 1.0), 2))

        # Company → products (1–3)
        for p_id in random.sample(product_ids, k=min(3, len(product_ids))):
            rel = random.choice(["contracted_with", "evaluating", "uses"])
            make_relation(c_eid, p_id, rel, weight=round(random.uniform(0.6, 1.0), 2))

        # Company → events (0–2)
        for e_id in random.sample(event_ids, k=min(2, len(event_ids))):
            make_relation(c_eid, e_id, "attended", weight=1.0)

        # Company → risks (based on churn_risk level)
        churn = float(company.get("churn_risk", 0.1))
        if churn > 0.5 and risk_ids:
            r_id = random.choice(risk_ids)
            make_relation(c_eid, r_id, "at_risk_of", weight=round(churn, 2))

    # Contacts → company + topics
    for contact in (contacts or []):
        cname = ""
        # We don't always have the company name; skip if missing
        contact_name = f"{contact.get('first_name','')} {contact.get('last_name','')}".strip()
        if not contact_name:
            continue
        ct_eid = make_entity(
            "contact", contact_name,
            properties={"title": contact.get("job_title"), "department": contact.get("department")},
            source_id=contact.get("id"),
        )
        if topic_ids:
            t_id = random.choice(topic_ids)
            make_relation(ct_eid, t_id, "raised", weight=round(random.uniform(0.3, 0.9), 2))
        if event_ids and random.random() > 0.6:
            e_id = random.choice(event_ids)
            make_relation(ct_eid, e_id, "attended", weight=1.0)

    # Remove the temp 'id' field used for internal tracking before DB insertion
    for ent in entities:
        ent.pop("id", None)

    return entities, relationships


if __name__ == "__main__":
    test_companies = [
        {"id": "c1", "name": "Acme Corp", "industry": "Technology", "account_tier": "gold", "churn_risk": 0.75},
        {"id": "c2", "name": "Globex Ltd", "industry": "Healthcare", "account_tier": "platinum", "churn_risk": 0.1},
    ]
    ents, rels = generate_entities(test_companies)
    print(f"Generated {len(ents)} entities and {len(rels)} relationships")