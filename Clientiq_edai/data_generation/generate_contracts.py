# Contracts generation
"""
ClientIQ — Contract Generator (standalone module)
Generates realistic enterprise contracts with full legal terms text.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import Any, Dict, List

fake = Faker()
random.seed(42)

CONTRACT_TYPES   = ["saas", "professional_services", "support", "partnership", "nda"]
CONTRACT_WEIGHTS = [50, 20, 15, 10, 5]

CURRENCIES = ["USD", "EUR", "GBP"]
CURRENCY_WEIGHTS = [75, 15, 10]

# Value ranges by contract type (USD)
VALUE_RANGES = {
    "saas":                 (12_000,  600_000),
    "professional_services":(25_000,  300_000),
    "support":              (5_000,   80_000),
    "partnership":          (50_000, 2_000_000),
    "nda":                  (0,       0),
}

TITLES = {
    "saas": [
        "Enterprise SaaS License Agreement",
        "Annual Platform Subscription Agreement",
        "Software-as-a-Service Master Agreement",
        "Cloud Platform Enterprise License",
    ],
    "professional_services": [
        "Professional Services Statement of Work",
        "Implementation Services Agreement",
        "Custom Development SOW",
        "Data Migration Services Agreement",
    ],
    "support": [
        "Premium Support & Maintenance Agreement",
        "Enterprise Technical Support Contract",
        "Priority Support SLA Agreement",
    ],
    "partnership": [
        "Strategic Partnership Framework Agreement",
        "Reseller Partnership Agreement",
        "Technology Alliance Agreement",
    ],
    "nda": [
        "Mutual Non-Disclosure Agreement",
        "Confidentiality Agreement",
    ],
}

TERMS_TEMPLATES = {
    "saas": (
        "This Software-as-a-Service Agreement ('Agreement') is entered into between the parties "
        "as of the Effective Date. Licensor grants Licensee a non-exclusive, non-transferable right "
        "to access and use the Platform for Licensee's internal business purposes. "
        "Service Level: Licensor guarantees 99.9% uptime measured monthly. In the event of SLA breach, "
        "Licensee is entitled to service credits of 10% of monthly fees per 0.1% uptime shortfall. "
        "Data: All data submitted by Licensee remains the sole property of Licensee. "
        "Licensor shall not access Licensee data except as required to provide the Service. "
        "Termination: Either party may terminate with 90 days written notice. "
        "Licensor may terminate immediately for material breach not cured within 30 days. "
        "Limitation of Liability: In no event shall either party be liable for indirect, incidental, "
        "or consequential damages. Licensor's aggregate liability shall not exceed fees paid in the "
        "12 months preceding the claim. Governing Law: This agreement is governed by the laws of Delaware, USA."
    ),
    "professional_services": (
        "This Statement of Work ('SOW') describes the professional services to be delivered by Provider. "
        "Deliverables and timeline are detailed in Exhibit A. Payment: 30% upon signing, 40% at milestone 1, "
        "30% upon final acceptance. Change requests must be submitted in writing and may affect timeline and cost. "
        "Intellectual Property: All work product created under this SOW shall be owned by Client upon full payment. "
        "Provider retains rights to pre-existing methodologies and tools. Confidentiality provisions of the "
        "Master Services Agreement apply. Warranty: Provider warrants deliverables will conform to specifications "
        "for 90 days following acceptance."
    ),
    "support": (
        "This Support Agreement defines the technical support services provided by Vendor. "
        "Response Times: P1 Critical — 1 hour; P2 High — 4 hours; P3 Medium — 1 business day; P4 Low — 3 business days. "
        "Support Hours: 24/7 for P1 and P2; business hours (09:00–18:00 local) for P3 and P4. "
        "Scope: Includes bug fixes, patch updates, and platform upgrades. Excludes custom development. "
        "Escalation: P1 issues escalate to Engineering VP within 2 hours if unresolved. "
        "Root Cause Analysis: Formal RCA document delivered within 5 business days of P1 resolution."
    ),
    "nda": (
        "This Non-Disclosure Agreement ('NDA') is entered into to protect confidential information shared "
        "between the parties in connection with a potential business relationship. 'Confidential Information' "
        "includes all technical, financial, and business information disclosed by either party. "
        "Obligations: Each party agrees to (i) maintain strict confidentiality, (ii) use information solely "
        "for the Purpose, and (iii) limit disclosure to employees with need-to-know. "
        "Exclusions: Information is not confidential if it is publicly known, independently developed, "
        "or rightfully received from a third party. Term: 3 years from the Effective Date."
    ),
}


def generate_contract(
    company_id:     str,
    opportunity_id: str = None,
    company_revenue: float = 100_000,
) -> Dict[str, Any]:
    """Generate a single enterprise contract."""
    ctype = random.choices(CONTRACT_TYPES, weights=CONTRACT_WEIGHTS)[0]

    lo, hi = VALUE_RANGES[ctype]
    # Scale value to company size
    scale = min(3.0, max(0.5, company_revenue / 1_000_000))
    value = round(random.uniform(lo, hi) * scale, 2) if hi > 0 else 0.0

    currency = random.choices(CURRENCIES, weights=CURRENCY_WEIGHTS)[0]

    # Duration: 1, 2, or 3 years
    duration_years = random.choices([1, 2, 3], weights=[50, 30, 20])[0]
    days_ago  = random.randint(30, 365)
    start_dt  = datetime.utcnow() - timedelta(days=days_ago)
    end_dt    = start_dt + timedelta(days=365 * duration_years)

    # Status based on end date
    now = datetime.utcnow()
    if end_dt < now:
        status = random.choices(["expired", "terminated"], weights=[80, 20])[0]
    else:
        status = random.choices(["active", "active", "active", "draft"], weights=[80, 10, 5, 5])[0]

    terms = TERMS_TEMPLATES.get(ctype, TERMS_TEMPLATES["saas"])
    title = random.choice(TITLES.get(ctype, ["Service Agreement"]))

    return {
        "company_id":     company_id,
        "opportunity_id": opportunity_id,
        "title":          title,
        "contract_type":  ctype,
        "value":          value,
        "currency":       currency,
        "start_date":     start_dt.date().isoformat(),
        "end_date":       end_dt.date().isoformat(),
        "auto_renew":     random.choice([True, False]),
        "status":         status,
        "terms_text":     terms,
        "signed_at":      (start_dt - timedelta(days=random.randint(3, 30))).isoformat(),
    }


def generate_contracts_for_companies(
    companies: List[Dict],
    opportunities_by_company: Dict[str, List[Dict]] = None,
) -> List[Dict[str, Any]]:
    """Generate contracts for a batch of companies."""
    opp_map = opportunities_by_company or {}
    contracts = []

    for company in companies:
        cid      = company["id"]
        revenue  = float(company.get("annual_revenue") or 100_000)
        tier     = company.get("account_tier", "silver")
        opps     = opp_map.get(cid, [])
        opp_ids  = [o.get("id") for o in opps if o.get("id")]

        # Number of contracts by tier
        n_map = {"platinum": (3, 6), "gold": (2, 4), "silver": (1, 3), "bronze": (1, 2)}
        lo, hi = n_map.get(tier, (1, 3))
        n = random.randint(lo, hi)

        for i in range(n):
            opp_id = opp_ids[i] if i < len(opp_ids) else None
            contracts.append(
                generate_contract(cid, opportunity_id=opp_id, company_revenue=revenue)
            )

    return contracts


if __name__ == "__main__":
    test = [{"id": "c1", "annual_revenue": 5_000_000, "account_tier": "gold"}]
    result = generate_contracts_for_companies(test)
    print(f"Generated {len(result)} contracts")
    for c in result:
        print(f"  {c['contract_type']} | ${c['value']:,.0f} {c['currency']} | {c['status']} | {c['start_date']}→{c['end_date']}")