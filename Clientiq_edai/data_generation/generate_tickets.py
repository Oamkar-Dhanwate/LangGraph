# Support tickets generation
"""
ClientIQ — Support Ticket Generator (standalone module)
Generates realistic enterprise support tickets with lifecycle states.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import Any, Dict, List

fake = Faker()
random.seed(42)

TICKET_TEMPLATES = [
    # ── Performance ───────────────────────────────────────────────────────────
    dict(
        title="Platform performance degradation during peak hours",
        description=(
            "Our team is experiencing significant slowdowns between 09:00–11:00 EST every weekday. "
            "Page load times have increased from ~300ms to 8–12 seconds. This is impacting our morning "
            "standup reporting and SLA commitments to our own customers. We need an urgent investigation."
        ),
        priority="critical", category="performance",
    ),
    # ── Authentication ────────────────────────────────────────────────────────
    dict(
        title="SSO login failure for subset of users after Okta migration",
        description=(
            "Following our Okta tenant migration completed on Monday, approximately 40 out of 180 users "
            "are unable to log in via SSO. They receive 'SAML assertion validation failed' errors. "
            "Direct login with username/password works. Rollback is not feasible — need urgent fix."
        ),
        priority="high", category="authentication",
    ),
    # ── Data Quality ──────────────────────────────────────────────────────────
    dict(
        title="Data sync discrepancy — records missing from API output",
        description=(
            "We've identified that records created via the bulk import API are not appearing in the "
            "GET /records endpoint for up to 90 minutes. Our downstream ETL pipeline depends on near-real-time "
            "availability. This is causing data gaps in our analytics warehouse. Approximately 2,300 records affected."
        ),
        priority="high", category="data_sync",
    ),
    # ── Billing ───────────────────────────────────────────────────────────────
    dict(
        title="Invoice discrepancy — overcharged for inactive seats",
        description=(
            "Our March invoice shows charges for 420 active seats. According to our internal license management "
            "system, only 312 seats have been activated. We've already deprovisioned 108 users but the billing "
            "system has not reflected this. Requesting immediate correction and credit note."
        ),
        priority="medium", category="billing",
    ),
    # ── Integration ───────────────────────────────────────────────────────────
    dict(
        title="Webhook events not delivered to our endpoint",
        description=(
            "Since last Thursday, webhook events for 'record.updated' are not being delivered to our registered "
            "endpoint (https://api.ourcompany.com/webhooks). We've confirmed our endpoint is healthy — it returns "
            "200 OK and our firewall allows inbound from your IP ranges. Delivery logs show events in 'pending' state."
        ),
        priority="high", category="integration",
    ),
    # ── Feature Request ───────────────────────────────────────────────────────
    dict(
        title="Feature request: bulk CSV export with custom field selection",
        description=(
            "We need the ability to export records to CSV with a custom field selection rather than exporting "
            "all 80+ fields. Our compliance team only needs specific columns and the current full export "
            "(650MB+ files) is impractical. This would significantly improve our monthly reporting workflow."
        ),
        priority="low", category="feature_request",
    ),
    # ── Security ─────────────────────────────────────────────────────────────
    dict(
        title="Suspicious login activity detected — possible unauthorised access",
        description=(
            "Our security team detected login events from an IP address (185.220.xxx.xxx — flagged as Tor exit node) "
            "for one of our administrator accounts at 03:14 UTC. The account was locked immediately. "
            "We need a full access log for this account for the past 30 days and confirmation of what data was accessed."
        ),
        priority="critical", category="security",
    ),
    # ── Onboarding ────────────────────────────────────────────────────────────
    dict(
        title="New user provisioning failing via SCIM API",
        description=(
            "We're using your SCIM 2.0 API to automate user provisioning from Azure AD. New users added to the "
            "assigned group are not being created in the platform. The SCIM API returns 201 Created but no user "
            "appears. This is blocking our onboarding for a 50-person team starting Monday."
        ),
        priority="high", category="onboarding",
    ),
]

STATUSES        = ["open", "in_progress", "pending_customer", "resolved", "closed"]
STATUS_WEIGHTS  = [15, 25, 10, 30, 20]

RESOLUTIONS = [
    "Root cause identified as a misconfiguration in the load balancer health check. Fix deployed to production at {time}. Monitoring for 24 hours.",
    "Issue reproduced in staging environment. Engineering team deployed a patch. Customer confirmed resolution.",
    "Configuration error on customer's firewall rules identified. Provided detailed remediation steps. Customer confirmed fixed.",
    "Database replication lag caused by a long-running migration job. Job completed; replication caught up. Proactive alerts added.",
    "Third-party API dependency was rate-limiting requests. Implemented retry logic and caching. Customer verified resolution.",
    "SAML certificate mismatch after provider migration. Updated certificate in IdP settings. All users now able to authenticate.",
]


def generate_ticket(
    company_id: str,
    contact_id:  str = None,
    base_health: float = 70,
) -> Dict[str, Any]:
    """
    Generate a single support ticket.

    Args:
        company_id:  UUID of the company
        contact_id:  UUID of the reporting contact (optional)
        base_health: Company health score — lower = more critical tickets
    """
    tmpl = random.choice(TICKET_TEMPLATES)

    # Skew toward more critical tickets for unhealthy accounts
    if base_health < 40:
        priority = random.choices(
            ["critical", "high", "medium", "low"],
            weights=[35, 40, 20, 5]
        )[0]
    elif base_health < 65:
        priority = random.choices(
            ["critical", "high", "medium", "low"],
            weights=[15, 35, 35, 15]
        )[0]
    else:
        priority = random.choices(
            ["critical", "high", "medium", "low"],
            weights=[5, 20, 45, 30]
        )[0]

    status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]

    days_ago    = random.randint(0, 270)
    opened_at   = datetime.utcnow() - timedelta(days=days_ago)
    resolved_at = None
    resolution  = None

    if status in ("resolved", "closed"):
        resolve_days = random.randint(1, 21)
        resolved_at  = (opened_at + timedelta(days=resolve_days)).isoformat()
        resolution   = random.choice(RESOLUTIONS).replace(
            "{time}", (opened_at + timedelta(days=resolve_days)).strftime("%H:%M UTC")
        )

    # SLA response time by priority
    response_hrs_map = {
        "critical": (0.5, 4),
        "high":     (1,   12),
        "medium":   (4,   48),
        "low":      (8,   72),
    }
    lo, hi = response_hrs_map.get(priority, (4, 48))
    first_response_hrs = round(random.uniform(lo, hi), 1)
    resolution_hrs     = round(random.uniform(first_response_hrs, first_response_hrs * 12), 1) if resolved_at else None

    # Sentiment: critical tickets are more negative
    sentiment_map = {"critical": -0.6, "high": -0.35, "medium": -0.1, "low": 0.05}
    base_sent     = sentiment_map.get(priority, -0.1)
    sentiment     = round(max(-1.0, min(1.0, base_sent + random.gauss(0, 0.12))), 4)

    return {
        "company_id":         company_id,
        "contact_id":         contact_id,
        "ticket_number":      f"TKT-{random.randint(10000, 99999)}",
        "title":              tmpl["title"],
        "description":        tmpl["description"],
        "priority":           priority,
        "status":             status,
        "category":           tmpl["category"],
        "resolution":         resolution,
        "sentiment_score":    sentiment,
        "first_response_hrs": first_response_hrs,
        "resolution_hrs":     resolution_hrs,
        "opened_at":          opened_at.isoformat(),
        "resolved_at":        resolved_at,
    }


def generate_tickets_for_companies(
    companies: List[Dict],
    contacts_by_company: Dict[str, List[Dict]],
) -> List[Dict[str, Any]]:
    """Generate support tickets for all companies."""
    tickets = []
    for company in companies:
        cid     = company["id"]
        health  = float(company.get("health_score", 70) or 70)
        contacts = contacts_by_company.get(cid, [])

        # Unhealthy accounts generate more tickets
        if health < 40:
            num = random.randint(12, 25)
        elif health < 65:
            num = random.randint(5, 14)
        else:
            num = random.randint(1, 7)

        for _ in range(num):
            contact_id = random.choice(contacts)["id"] if contacts else None
            tickets.append(generate_ticket(cid, contact_id, base_health=health))

    return tickets


if __name__ == "__main__":
    test = [{"id": "c1", "health_score": 30}]
    result = generate_tickets_for_companies(test, {})
    print(f"Generated {len(result)} tickets for low-health company")
    from collections import Counter
    print(Counter(t["priority"] for t in result))