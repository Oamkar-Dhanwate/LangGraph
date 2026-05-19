# Generate clients/contacts
"""
ClientIQ — CRM Data Generator
Generates realistic enterprise companies and contacts using Faker.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any

fake = Faker()
random.seed(42)
Faker.seed(42)

INDUSTRIES = ["Technology", "Financial Services", "Healthcare", "Manufacturing",
               "Retail", "Logistics", "Education", "Media", "Real Estate", "Energy"]

TIERS = ["bronze", "silver", "gold", "platinum"]
TIER_WEIGHTS = [0.3, 0.4, 0.2, 0.1]

DEPARTMENTS = ["IT", "Finance", "Operations", "Sales", "Marketing",
               "HR", "Legal", "Engineering", "Product", "C-Suite"]

TITLES = {
    "C-Suite": ["CEO", "CTO", "CFO", "COO", "CMO", "CIO"],
    "IT": ["IT Manager", "Systems Administrator", "IT Director", "DevOps Lead"],
    "Finance": ["Finance Manager", "Controller", "VP Finance", "CFO"],
    "Sales": ["VP Sales", "Account Executive", "Sales Director", "Revenue Officer"],
    "Operations": ["Operations Manager", "COO", "Head of Operations"],
}


def generate_company(idx: int) -> Dict[str, Any]:
    tier = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
    size = random.choice(["startup", "smb", "mid_market", "enterprise"])

    revenue_range = {
        "startup": (100_000, 2_000_000),
        "smb": (2_000_000, 20_000_000),
        "mid_market": (20_000_000, 200_000_000),
        "enterprise": (200_000_000, 5_000_000_000),
    }
    lo, hi = revenue_range[size]
    health = round(random.gauss(68, 18), 2)
    health = max(5, min(100, health))
    churn = round(max(0.01, min(0.99, 1 - health / 100 + random.gauss(0, 0.1))), 4)

    return {
        "name": fake.company(),
        "industry": random.choice(INDUSTRIES),
        "size_category": size,
        "annual_revenue": round(random.uniform(lo, hi), 2),
        "country": random.choices(
            ["United States", "United Kingdom", "Germany", "Canada", "Australia", "India", "Singapore"],
            weights=[50, 15, 10, 8, 6, 6, 5]
        )[0],
        "website": fake.url(),
        "account_tier": tier,
        "health_score": health,
        "churn_risk": churn,
    }


def generate_contact(company_id: str, is_primary: bool = False) -> Dict[str, Any]:
    department = random.choice(DEPARTMENTS)
    title_pool = TITLES.get(department, ["Manager", "Director", "VP", "Lead"])
    title = random.choice(title_pool)
    sentiment = round(random.gauss(0.1, 0.35), 4)
    sentiment = max(-1.0, min(1.0, sentiment))
    days_ago = random.randint(0, 90)

    return {
        "company_id": company_id,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.company_email(),
        "phone": fake.phone_number(),
        "job_title": title,
        "department": department,
        "is_primary": is_primary,
        "sentiment_score": sentiment,
        "last_contacted": (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
    }


def generate_companies(n: int = 50) -> List[Dict]:
    return [generate_company(i) for i in range(n)]


def generate_contacts_for_companies(companies: List[Dict]) -> List[Dict]:
    contacts = []
    for c in companies:
        company_id = c.get("id") or c.get("_temp_id", "")
        num_contacts = random.randint(2, 8)
        for j in range(num_contacts):
            contact = generate_contact(company_id, is_primary=(j == 0))
            contacts.append(contact)
    return contacts


if __name__ == "__main__":
    companies = generate_companies(50)
    print(f"Generated {len(companies)} companies")
    for i, c in enumerate(companies[:3]):
        print(f"  {i+1}. {c['name']} | {c['industry']} | health={c['health_score']}")