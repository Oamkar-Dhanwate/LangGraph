# Email corpus generation
"""
ClientIQ — Email Data Generator
Generates realistic enterprise email threads with temporal consistency.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any

fake = Faker()
random.seed(42)

EMAIL_TEMPLATES = {
    "positive": [
        ("Re: Partnership Update", "Hi {name},\n\nThank you for the excellent QBR session yesterday. The roadmap you presented aligns perfectly with our strategic objectives for Q3. We are particularly excited about the new API integrations and the performance improvements you demonstrated.\n\nOur team has reviewed the proposal and we are ready to proceed with the expanded package. Could we schedule a contract review call this week?\n\nBest regards,\n{sender}"),
        ("Q2 Results - Exceeding Targets", "Dear {name},\n\nI wanted to reach out and share that your platform has been instrumental in helping us exceed our Q2 targets by 23%. The analytics features have given our team unprecedented visibility into our pipeline.\n\nWe would love to explore upgrading our subscription to the Enterprise tier to unlock the advanced reporting capabilities. Please have your sales team reach out.\n\nWarm regards,\n{sender}"),
        ("Renewal Discussion", "Hi {name},\n\nWith our annual renewal coming up next month, I wanted to proactively reach out. We've been thrilled with the service this year — the uptime has been flawless and the customer success team has been incredibly responsive.\n\nWe're planning to expand usage to two additional departments and would appreciate a call to discuss the enterprise pricing options.\n\nBest,\n{sender}"),
    ],
    "neutral": [
        ("Question About API Rate Limits", "Hi {name},\n\nI have a quick question about the API rate limits for our current subscription plan. We're building an integration that will require approximately 500 calls per hour during peak periods.\n\nCould you confirm whether our current plan supports this, or if we need to upgrade? Also, is there a sandbox environment we can use for testing?\n\nThanks,\n{sender}"),
        ("Upcoming Maintenance Window", "Hello {name},\n\nJust wanted to check in regarding the maintenance window scheduled for this weekend. Can you confirm the expected downtime duration and whether there will be any impact on the reporting module?\n\nWe have a board presentation on Monday and want to ensure all data is current.\n\nRegards,\n{sender}"),
        ("Meeting Notes Follow-up", "Hi {name},\n\nFollowing up on our call last week regarding the integration timeline. As discussed, our technical team is available the week of the 15th to begin the implementation phase.\n\nPlease send over the technical documentation when you have a chance.\n\nThanks,\n{sender}"),
    ],
    "negative": [
        ("Service Disruption Impact", "Dear {name},\n\nI'm writing to formally document the significant business impact caused by the service outage last Tuesday. Our team was unable to access the platform for 4 hours during peak business hours, resulting in a loss of approximately $50,000 in delayed transactions.\n\nThis is the third incident in two months. We need a comprehensive post-mortem and a formal SLA credit. If the reliability issues continue, we will need to evaluate alternative vendors.\n\nRegards,\n{sender}"),
        ("Unresolved Support Ticket", "Hi {name},\n\nI'm escalating ticket #48291 which has been open for 12 days with no resolution. The data sync issues are affecting our daily reporting and our leadership team is frustrated.\n\nI need this escalated to your engineering team immediately. Our contract renews in 60 days and the current service level is not acceptable.\n\nFrustrated,\n{sender}"),
        ("Re: Contract Terms Concern", "Dear {name},\n\nAfter our legal team reviewed the proposed contract amendment, we have significant concerns about the new data retention clauses and the changes to the SLA terms.\n\nThe reduction in uptime guarantee from 99.9% to 99.5% is unacceptable for our business-critical operations. We also need clarification on the data portability provisions.\n\nWe are placing the renewal on hold pending these clarifications.\n\nBest,\n{sender}"),
    ],
}


def generate_email(company_id: str, contact_id: str = None, sentiment_label: str = "neutral") -> Dict[str, Any]:
    template_pool = EMAIL_TEMPLATES.get(sentiment_label, EMAIL_TEMPLATES["neutral"])
    subject, body_template = random.choice(template_pool)

    sender_name = fake.name()
    body = body_template.format(name=fake.first_name(), sender=sender_name)

    # Sentiment scores
    sentiment_scores = {"positive": 0.45, "neutral": 0.02, "negative": -0.48}
    base_score = sentiment_scores.get(sentiment_label, 0.0)
    noise = random.gauss(0, 0.1)
    score = max(-1.0, min(1.0, base_score + noise))

    days_ago = random.randint(0, 180)

    return {
        "company_id": company_id,
        "contact_id": contact_id,
        "direction": random.choice(["inbound", "outbound"]),
        "subject": subject,
        "body": body,
        "sentiment_score": round(score, 4),
        "sentiment_label": sentiment_label,
        "sent_at": (datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))).isoformat(),
    }


def generate_emails_for_companies(companies: List[Dict], contacts_by_company: Dict) -> List[Dict]:
    emails = []
    for company in companies:
        cid = company["id"]
        company_contacts = contacts_by_company.get(cid, [])

        # Number of emails based on health (unhealthy = more emails = more issues)
        health = float(company.get("health_score", 70))
        num_emails = random.randint(5, 20) if health >= 60 else random.randint(15, 40)

        for _ in range(num_emails):
            # Weight sentiment by health
            if health >= 70:
                label = random.choices(["positive", "neutral", "negative"], weights=[40, 45, 15])[0]
            elif health >= 40:
                label = random.choices(["positive", "neutral", "negative"], weights=[20, 45, 35])[0]
            else:
                label = random.choices(["positive", "neutral", "negative"], weights=[10, 30, 60])[0]

            contact_id = random.choice(company_contacts)["id"] if company_contacts else None
            email = generate_email(cid, contact_id, label)
            emails.append(email)

    return emails