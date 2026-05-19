# Meeting notes generation
"""
ClientIQ — Meeting, Call, Ticket, Contract Generators
Generates interconnected enterprise communications data.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any

fake = Faker()
random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# MEETINGS
# ─────────────────────────────────────────────────────────────────────────────

MEETING_NOTES = {
    "qbr": [
        "Quarterly Business Review — covered YTD metrics, platform adoption rates (up 34%), upcoming feature releases, and renewal terms. Client expressed satisfaction with support responsiveness. Action items: share roadmap deck, schedule Executive Sponsor alignment call.",
        "Q3 QBR: Revenue growth discussion, integration roadmap review. Client flagged concerns around API performance during peak hours. We committed to a dedicated infrastructure review. Renewal probability assessed at 85%.",
    ],
    "demo": [
        "Product demo: Showcased the new analytics dashboard and AI reporting features. Client team of 5 was highly engaged. Technical questions around data export formats and SSO configuration. Next step: POC proposal.",
        "Discovery and demo session. Client evaluating us against two competitors. Key differentiators discussed: real-time analytics, compliance certifications, and dedicated CSM model. Decision expected in 3 weeks.",
    ],
    "renewal": [
        "Renewal negotiation call. Client requested 15% discount citing competitive offers. We proposed a 3-year commitment in exchange for 10% discount + additional professional services hours. Client to discuss internally.",
        "Early renewal discussion — client wants to upgrade from Professional to Enterprise tier. Contract value increase of $180,000. Legal review of updated MSA terms requested.",
    ],
    "support": [
        "Emergency call regarding data sync failure impacting reporting. Root cause identified as API token expiration. Resolved within the call. Client frustrated — third issue this quarter. Escalated to CSM leadership.",
        "Technical support meeting to resolve ongoing performance issues. Engineering team joined. Identified configuration error on client side. Provided remediation guide and follow-up monitoring plan.",
    ],
}

MEETING_TYPES = ["discovery", "demo", "qbr", "renewal", "support", "kickoff", "other"]


def generate_meeting(company_id: str, meeting_type: str = None) -> Dict[str, Any]:
    mtype = meeting_type or random.choice(MEETING_TYPES)
    notes_pool = MEETING_NOTES.get(mtype, MEETING_NOTES["qbr"])
    notes = random.choice(notes_pool)

    health_signal = random.gauss(0, 0.25)
    sentiment = max(-1.0, min(1.0, health_signal))

    days_ago = random.randint(0, 270)
    attendees = [
        {"name": fake.name(), "email": fake.company_email(), "role": fake.job()}
        for _ in range(random.randint(2, 6))
    ]
    action_items = [
        {"owner": fake.name(), "task": fake.sentence(nb_words=8), "due_date": (datetime.utcnow() + timedelta(days=random.randint(3, 21))).strftime("%Y-%m-%d")}
        for _ in range(random.randint(1, 4))
    ]

    return {
        "company_id": company_id,
        "title": f"{mtype.upper().replace('_',' ')} - {fake.bs().title()}",
        "meeting_type": mtype,
        "attendees": attendees,
        "notes": notes,
        "action_items": action_items,
        "sentiment_score": round(sentiment, 4),
        "duration_mins": random.choice([30, 45, 60, 90]),
        "scheduled_at": (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CALL TRANSCRIPTS
# ─────────────────────────────────────────────────────────────────────────────

CALL_TRANSCRIPTS = [
    ("Agent: Thank you for calling. How can I help today?\nClient: We're seeing some unexpected latency issues in the dashboard. It started around 9 AM this morning.\nAgent: I understand. Let me pull up your account. Can you confirm which region you're on?\nClient: We're on US-East.\nAgent: I can see elevated response times on that cluster. Our team is already investigating. I'll create a P1 ticket and have someone contact you within 30 minutes.\nClient: That's appreciated, but this has happened twice this month already. We need a permanent fix.\nAgent: I completely understand your frustration. I'll escalate this to our infrastructure team and ensure you receive a full RCA.", "support"),
    ("Sales Rep: Hi {name}, calling to follow up on our proposal from last week.\nClient: Yes, I was just discussing it with our team. We're very interested in the Enterprise tier.\nSales Rep: Wonderful! What aspects resonated most with your team?\nClient: Primarily the advanced analytics and the dedicated CSM model. We've had issues with support responsiveness in the past.\nSales Rep: Those are exactly the areas where Enterprise clients see the most value. Would you be available Thursday for a call with our VP of Sales?\nClient: Thursday at 2pm works perfectly.", "sales"),
    ("CSM: Good morning. Wanted to check in as we approach your renewal date.\nClient: Thanks for reaching out. Honestly, I've been meaning to call. We've had a few concerns.\nCSM: I appreciate you being candid. Can you share what's been top of mind?\nClient: The reporting module has been slow, and our IT team has been frustrated with the API documentation.\nCSM: Those are valid concerns and I want to address both. Can we schedule a technical session with our engineering team this week?\nClient: Yes, let's do that. We want to make this work.", "renewal"),
]


def generate_call(company_id: str, contact_id: str = None) -> Dict[str, Any]:
    transcript_text, call_type = random.choice(CALL_TRANSCRIPTS)
    transcript_text = transcript_text.replace("{name}", fake.first_name())

    sentiment = round(random.gauss(0.0, 0.3), 4)
    duration = random.randint(300, 3600)
    days_ago = random.randint(0, 180)
    topics = random.sample(["pricing", "renewal", "support", "integration", "performance", "roadmap", "escalation", "onboarding"], k=random.randint(2, 4))

    return {
        "company_id": company_id,
        "contact_id": contact_id,
        "call_type": call_type,
        "duration_secs": duration,
        "transcript": transcript_text,
        "summary": fake.sentence(nb_words=20),
        "sentiment_score": sentiment,
        "key_topics": topics,
        "called_at": (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKETS
# ─────────────────────────────────────────────────────────────────────────────

TICKET_TEMPLATES = [
    ("API Integration Failure — Dashboard Not Loading", "Our integration with your API started failing at approximately 14:30 UTC. The dashboard is returning a 502 error for all our users. This is affecting our sales team's ability to access real-time data during a critical campaign period.", "high", "integration"),
    ("Data Export Missing Fields", "When exporting client data to CSV, several fields including last_modified and custom_attributes are missing from the output. This has been happening since last Tuesday's platform update.", "medium", "data_export"),
    ("SSO Configuration Issue", "Following our Okta SSO setup, users are receiving a 'SAML assertion expired' error intermittently. The issue affects approximately 20% of login attempts.", "high", "authentication"),
    ("Performance Degradation During Peak Hours", "Between 9 AM - 11 AM EST our platform response times increase from ~200ms to 4000ms+. This has been consistent for the past two weeks.", "critical", "performance"),
    ("Billing Discrepancy", "Our invoice for last month shows charges for 500 active users, but our system shows only 340 active accounts. Please review and issue a credit for the difference.", "medium", "billing"),
    ("Feature Request: Bulk User Import", "We have 200+ users to onboard and the current one-by-one process is inefficient. We need a CSV bulk import feature.", "low", "feature_request"),
]

TICKET_STATUSES = ["open", "in_progress", "pending_customer", "resolved", "closed"]


def generate_ticket(company_id: str, contact_id: str = None, ticket_number: str = None) -> Dict[str, Any]:
    title, desc, priority, category = random.choice(TICKET_TEMPLATES)
    status = random.choices(TICKET_STATUSES, weights=[20, 25, 15, 25, 15])[0]
    days_ago = random.randint(0, 180)
    opened = datetime.utcnow() - timedelta(days=days_ago)
    resolved_at = None
    resolution = None

    if status in ["resolved", "closed"]:
        resolve_days = random.randint(1, 14)
        resolved_at = (opened + timedelta(days=resolve_days)).isoformat()
        resolution = f"Issue resolved by {fake.name()} from engineering. Root cause: {fake.sentence(nb_words=12)}. Prevention steps implemented."

    ticket_num = ticket_number or f"TKT-{random.randint(10000, 99999)}"
    sentiment = -0.3 if priority in ["high", "critical"] else -0.1

    return {
        "company_id": company_id,
        "contact_id": contact_id,
        "ticket_number": ticket_num,
        "title": title,
        "description": desc,
        "priority": priority,
        "status": status,
        "category": category,
        "resolution": resolution,
        "sentiment_score": round(sentiment + random.gauss(0, 0.15), 4),
        "first_response_hrs": random.randint(1, 48),
        "resolution_hrs": random.randint(4, 240) if resolved_at else None,
        "opened_at": opened.isoformat(),
        "resolved_at": resolved_at,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CONTRACTS
# ─────────────────────────────────────────────────────────────────────────────

CONTRACT_TYPES = ["saas", "professional_services", "support", "partnership"]

def generate_contract(company_id: str, opportunity_id: str = None) -> Dict[str, Any]:
    c_type = random.choice(CONTRACT_TYPES)
    revenue_map = {
        "saas": (12000, 500000),
        "professional_services": (25000, 200000),
        "support": (5000, 50000),
        "partnership": (50000, 1000000),
    }
    lo, hi = revenue_map[c_type]
    value = round(random.uniform(lo, hi), 2)
    years = random.choice([1, 2, 3])
    days_ago = random.randint(30, 365)
    start = datetime.utcnow() - timedelta(days=days_ago)
    end = start + timedelta(days=365 * years)

    return {
        "company_id": company_id,
        "opportunity_id": opportunity_id,
        "title": f"{c_type.replace('_',' ').title()} Agreement — {fake.bs().title()}",
        "contract_type": c_type,
        "value": value,
        "currency": "USD",
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "auto_renew": random.choice([True, False]),
        "status": random.choices(["active", "active", "active", "expired", "terminated"], weights=[60, 15, 10, 10, 5])[0],
        "terms_text": f"This {c_type} agreement between the parties sets forth the terms and conditions for service delivery. Service credits apply for SLA breaches. Data ownership remains with the client. Either party may terminate with 90-day written notice.",
        "signed_at": (start - timedelta(days=random.randint(5, 30))).isoformat(),
    }


def generate_all_communications(companies: List[Dict], contacts_by_company: Dict) -> Dict:
    meetings, calls, tickets, contracts = [], [], [], []
    for c in companies:
        cid = c["id"]
        company_contacts = contacts_by_company.get(cid, [])
        contact_ids = [ct["id"] for ct in company_contacts]

        # Meetings
        num = random.randint(2, 10)
        for _ in range(num):
            meetings.append(generate_meeting(cid))

        # Calls
        for _ in range(random.randint(1, 6)):
            calls.append(generate_call(cid, random.choice(contact_ids) if contact_ids else None))

        # Tickets (unhealthy = more tickets)
        health = float(c.get("health_score", 70))
        n_tickets = random.randint(8, 20) if health < 50 else random.randint(1, 8)
        for _ in range(n_tickets):
            ticket_number = f"TKT-{len(tickets) + 1:05d}"
            tickets.append(generate_ticket(
                cid,
                random.choice(contact_ids) if contact_ids else None,
                ticket_number=ticket_number,
            ))

        # Contracts
        n_contracts = random.randint(1, 3)
        for _ in range(n_contracts):
            contracts.append(generate_contract(cid))

    return {"meetings": meetings, "calls": calls, "tickets": tickets, "contracts": contracts}
