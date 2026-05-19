# Sales pipeline generation
"""
ClientIQ — Sales Pipeline Generator
Generates realistic Opportunities across all pipeline stages
with temporal progression and realistic probability weighting.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any

fake = Faker()
random.seed(42)

STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]

STAGE_PROBABILITIES = {
    "prospecting":   (0, 15),
    "qualification": (15, 35),
    "proposal":      (35, 65),
    "negotiation":   (65, 85),
    "closed_won":    (100, 100),
    "closed_lost":   (0, 0),
}

STAGE_WEIGHTS = [25, 20, 20, 15, 12, 8]   # distribution across pipeline

SOURCES = [
    "Inbound Web", "Partner Referral", "Cold Outbound",
    "Event / Conference", "Existing Customer Expansion",
    "Social Selling", "Marketing Campaign",
]

OPPORTUNITY_NAMES = [
    "Enterprise Platform License",
    "Professional Services Engagement",
    "Annual SaaS Renewal + Expansion",
    "AI Analytics Module Add-on",
    "Enterprise Security Package",
    "Multi-site Deployment",
    "Data Integration Project",
    "Executive Dashboard Rollout",
    "Compliance Module Implementation",
    "API Platform Access",
    "Support & Maintenance Contract",
    "Cloud Migration Assistance",
]


def generate_opportunity(
    company_id: str,
    owner_id: str = None,
    annual_revenue: float = 100_000,
) -> Dict[str, Any]:
    """Generate a single sales opportunity for a company."""
    stage = random.choices(STAGES, weights=STAGE_WEIGHTS)[0]
    prob_lo, prob_hi = STAGE_PROBABILITIES[stage]
    probability = random.uniform(prob_lo, prob_hi)

    # Deal size correlates with company revenue
    base_deal = annual_revenue * random.uniform(0.02, 0.25)
    amount = round(base_deal * random.uniform(0.5, 2.0), 2)

    # Close date: future for open stages, past for closed
    if stage in ("closed_won", "closed_lost"):
        days_offset = -random.randint(1, 180)   # already closed
    else:
        days_offset = random.randint(14, 120)    # upcoming

    close_date = (datetime.utcnow() + timedelta(days=days_offset)).date().isoformat()

    return {
        "company_id":  company_id,
        "owner_id":    owner_id,
        "name":        random.choice(OPPORTUNITY_NAMES),
        "stage":       stage,
        "amount":      amount,
        "probability": round(probability, 1),
        "close_date":  close_date,
        "source":      random.choice(SOURCES),
        "notes":       fake.sentence(nb_words=15),
    }


def generate_pipeline(
    companies: List[Dict],
    user_ids: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate a full sales pipeline for all companies.

    Args:
        companies:  List of company dicts (must include 'id' and 'annual_revenue')
        user_ids:   Optional list of user IDs to assign as opportunity owners

    Returns:
        List of opportunity dicts
    """
    opportunities = []
    for company in companies:
        cid     = company.get("id", "")
        revenue = float(company.get("annual_revenue") or 100_000)

        # Number of opps scales with company size
        if revenue > 50_000_000:
            n = random.randint(3, 8)
        elif revenue > 5_000_000:
            n = random.randint(1, 5)
        else:
            n = random.randint(0, 3)

        for _ in range(n):
            owner = random.choice(user_ids) if user_ids else None
            opp   = generate_opportunity(cid, owner_id=owner, annual_revenue=revenue)
            opportunities.append(opp)

    return opportunities


def pipeline_summary(opportunities: List[Dict]) -> Dict[str, Any]:
    """Compute pipeline funnel statistics."""
    by_stage: Dict[str, List] = {s: [] for s in STAGES}
    for opp in opportunities:
        stage = opp.get("stage", "prospecting")
        by_stage.setdefault(stage, []).append(opp)

    summary = {}
    for stage, opps in by_stage.items():
        total_value = sum(float(o.get("amount", 0)) for o in opps)
        summary[stage] = {
            "count":       len(opps),
            "total_value": round(total_value, 2),
            "avg_value":   round(total_value / max(1, len(opps)), 2),
        }
    return summary


if __name__ == "__main__":
    # Quick smoke test
    test_companies = [
        {"id": "c1", "annual_revenue": 5_000_000},
        {"id": "c2", "annual_revenue": 200_000_000},
    ]
    opps = generate_pipeline(test_companies)
    print(f"Generated {len(opps)} opportunities")
    print(pipeline_summary(opps))