# Call transcripts generation
"""
ClientIQ — Call Transcript Generator (standalone module)
Generates realistic enterprise call transcripts with multi-turn dialogue.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import Any, Dict, List

fake = Faker()
random.seed(42)

CALL_TYPES    = ["sales", "support", "renewal", "escalation", "other"]
CALL_WEIGHTS  = [25, 35, 20, 10, 10]

# Extended transcript corpus
TRANSCRIPTS = [
    # ── Sales ─────────────────────────────────────────────────────────────────
    {
        "call_type":  "sales",
        "transcript": (
            "Sales Rep: Good morning {contact_name}, thanks for making time today.\n"
            "Client: Of course. We've been evaluating a few vendors and wanted to learn more about your platform.\n"
            "Sales Rep: Happy to help. To start, can you walk me through your current analytics stack and what gaps you're trying to fill?\n"
            "Client: We're using a combination of Tableau and some custom Python scripts. The pain point is real-time data — we can't see what's happening until the next morning.\n"
            "Sales Rep: That's exactly what our Event Stream module addresses. It processes and surfaces insights within 90 seconds of an event. Let me share my screen and walk you through a live demo.\n"
            "Client: Please do. We're also concerned about the migration complexity — we have about 200 data sources.\n"
            "Sales Rep: Our integration team has migrated clients with up to 500 sources. I can connect you with one of our solution architects this week."
        ),
        "sentiment_score": 0.42,
        "key_topics": ["product demo", "real-time analytics", "integration", "data migration"],
    },
    # ── Support Escalation ────────────────────────────────────────────────────
    {
        "call_type":  "escalation",
        "transcript": (
            "Support Manager: {contact_name}, I'm escalating this directly because I understand the urgency.\n"
            "Client: I appreciate that. This is the second outage this month. Our board presentation is tomorrow and we cannot pull reports right now.\n"
            "Support Manager: I completely understand. Our Site Reliability team identified a database replica lag issue 20 minutes ago and we have a hotfix deploying now. ETA is 15 minutes.\n"
            "Client: 15 minutes is cutting it close. I need a commitment from your leadership that this won't happen again.\n"
            "Support Manager: I can arrange a call with our VP of Engineering this week to walk through our infrastructure improvements. I'll also ensure you receive a formal RCA document within 48 hours.\n"
            "Client: That's acceptable. But I want it noted that we are evaluating our options at renewal.\n"
            "Support Manager: Noted, and I take that seriously. Resolving this now and following up proactively is our top priority."
        ),
        "sentiment_score": -0.58,
        "key_topics": ["outage", "escalation", "SLA breach", "renewal risk", "RCA"],
    },
    # ── Renewal ───────────────────────────────────────────────────────────────
    {
        "call_type":  "renewal",
        "transcript": (
            "CSM: {contact_name}, with renewal coming up next month, I wanted to check in on your experience this year.\n"
            "Client: Overall positive. The platform has delivered on what was promised during the sales process.\n"
            "CSM: Glad to hear that. We've been tracking your usage — you're at 87% platform utilization which is excellent. Have you explored the new AI summarization feature?\n"
            "Client: Not yet. Our team has been stretched thin. Can you walk me through it?\n"
            "CSM: Absolutely. It auto-generates meeting recaps and action items, which typically saves teams 30 minutes per meeting. I'll set up a dedicated enablement session next week.\n"
            "Client: That would be valuable. On the renewal, we're looking at expanding to two additional business units. What does that look like from a pricing standpoint?\n"
            "CSM: Great timing — we have an enterprise expansion pricing model that actually reduces per-seat cost as you scale. I'll have a proposal to you by end of week."
        ),
        "sentiment_score": 0.55,
        "key_topics": ["renewal", "expansion", "pricing", "feature adoption", "ROI"],
    },
    # ── QBR ──────────────────────────────────────────────────────────────────
    {
        "call_type":  "other",
        "transcript": (
            "CSM: Welcome to your Q3 Business Review, {contact_name}. I have your usage metrics and ROI analysis ready to share.\n"
            "Client: Perfect. Our CFO has been asking for justification on the spend, so this is timely.\n"
            "CSM: Understood. Looking at Q3 — your team processed 142,000 records through the platform, up 34% from Q2. Time savings are estimated at 1,200 hours.\n"
            "Client: At our average fully-loaded cost of $85 per hour, that's over $100,000 in value against an annual subscription of $60,000. That's a strong ROI story.\n"
            "CSM: Exactly. I'll include that calculation in the summary deck. Now, I also want to discuss the roadmap items you requested in Q2.\n"
            "Client: The bulk export feature — is that still scheduled for Q4?\n"
            "CSM: It's in the current sprint and on track for October release. I'll flag you for early beta access."
        ),
        "sentiment_score": 0.61,
        "key_topics": ["QBR", "ROI", "usage metrics", "product roadmap", "feature request"],
    },
    # ── Support ───────────────────────────────────────────────────────────────
    {
        "call_type":  "support",
        "transcript": (
            "Support: Thank you for calling support, {contact_name}. Can you describe what you're experiencing?\n"
            "Client: Our automated report jobs that run at 6 AM have been failing silently for the past three days. We only noticed because a downstream team flagged missing data.\n"
            "Support: I see. Let me pull up your job logs. I can see several timeout errors beginning Tuesday at 06:14 UTC. This correlates with a change we pushed to the scheduler service.\n"
            "Client: Can it be reverted?\n"
            "Support: I'm going to raise this with our infrastructure team right now. In the meantime, I can manually trigger the missed reports. Would that help?\n"
            "Client: Yes please — we need the last three days recovered.\n"
            "Support: Triggering now. You should see data populating within 20 minutes. I'll follow up via email once the root cause fix is deployed, and we'll add a monitoring alert to catch this class of failure going forward."
        ),
        "sentiment_score": -0.18,
        "key_topics": ["report failure", "scheduler", "data recovery", "monitoring"],
    },
]


def generate_call(
    company_id: str,
    contact_id:  str = None,
    contact_name: str = None,
) -> Dict[str, Any]:
    """Generate a single realistic call transcript."""
    tmpl = random.choice(TRANSCRIPTS)
    name = contact_name or fake.name()

    transcript = tmpl["transcript"].replace("{contact_name}", name)

    # Add slight score variation
    base_score = tmpl["sentiment_score"]
    score = round(max(-1.0, min(1.0, base_score + random.gauss(0, 0.1))), 4)

    duration   = random.randint(120, 4800)   # 2 min – 80 min
    days_ago   = random.randint(0, 180)

    return {
        "company_id":    company_id,
        "contact_id":    contact_id,
        "call_type":     tmpl["call_type"],
        "duration_secs": duration,
        "transcript":    transcript,
        "summary":       fake.sentence(nb_words=18),
        "sentiment_score": score,
        "key_topics":    tmpl["key_topics"],
        "called_at":     (datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(8, 18))).isoformat(),
    }


def generate_calls_for_companies(
    companies: List[Dict],
    contacts_by_company: Dict[str, List[Dict]],
) -> List[Dict[str, Any]]:
    """Generate calls for a batch of companies."""
    calls = []
    for company in companies:
        cid = company["id"]
        company_contacts = contacts_by_company.get(cid, [])

        num = random.randint(2, 8)
        for _ in range(num):
            if company_contacts:
                contact = random.choice(company_contacts)
                contact_id   = contact.get("id")
                contact_name = f"{contact.get('first_name','')} {contact.get('last_name','')}".strip()
            else:
                contact_id, contact_name = None, None

            calls.append(generate_call(cid, contact_id, contact_name))

    return calls


if __name__ == "__main__":
    test = [{"id": "c1"}]
    result = generate_calls_for_companies(test, {"c1": [{"id": "ct1", "first_name": "Jane", "last_name": "Smith"}]})
    print(f"Generated {len(result)} calls")
    print(result[0]["call_type"], "—", result[0]["sentiment_score"])