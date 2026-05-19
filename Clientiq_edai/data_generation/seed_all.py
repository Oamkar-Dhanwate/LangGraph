# Master seeder
"""
ClientIQ — Master Data Seeder
Orchestrates full data generation and loads all records into TiDB.

Run with:  python -m data_generation.seed_all
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
import random
from tqdm import tqdm
from sqlalchemy import func, select
from backend.utils.logger import logger
from backend.database.connection import engine, get_db_session
from backend.database.models import (
    Role, User, Company, Contact, Email, Meeting,
    CallTranscript, SupportTicket, Contract, Opportunity,
    HealthSnapshot, KGEntity, KGRelationship, AgentSession
)
from backend.services.auth_service import auth_service
from data_generation.generate_crm import generate_companies, generate_contacts_for_companies
from data_generation.generate_emails import generate_emails_for_companies
from data_generation.generate_meetings import generate_all_communications


async def seed_roles_and_users(session):
    """Seed RBAC roles and demo users."""
    logger.info("Seeding roles and users...")

    role_defs = [
        ("admin",   {"read_crm": True,  "read_financials": True,  "read_contracts": True,  "read_pii": True,  "export_data": True, "read_audit_logs": True}),
        ("manager", {"read_crm": True,  "read_financials": True,  "read_contracts": True,  "read_pii": False, "export_data": True, "read_audit_logs": False}),
        ("analyst", {"read_crm": True,  "read_financials": True,  "read_contracts": False, "read_pii": False, "export_data": False, "read_audit_logs": False}),
        ("viewer",  {"read_crm": True,  "read_financials": False, "read_contracts": False, "read_pii": False, "export_data": False, "read_audit_logs": False}),
    ]

    role_ids = {}
    for name, perms in role_defs:
        role = Role(name=name, permissions=perms)
        session.add(role)
        await session.flush()
        role_ids[name] = role.id

    # Demo users
    demo_users = [
        ("admin@clientiq.demo",   "admin123",    "Alex Admin",    "admin"),
        ("manager@clientiq.demo", "manager123",  "Morgan Manager","manager"),
        ("analyst@clientiq.demo", "analyst123",  "Sam Analyst",   "analyst"),
        ("viewer@clientiq.demo",  "viewer123",   "Val Viewer",    "viewer"),
    ]
    for email, password, name, role_name in demo_users:
        user = User(
            email=email,
            hashed_password=auth_service.hash_password(password),
            full_name=name,
            role_id=role_ids[role_name],
        )
        session.add(user)

    await session.flush()
    logger.info("Roles and users seeded")
    return role_ids


async def seed_companies_and_contacts(session, n_companies: int = 50):
    """Seed companies and contacts."""
    logger.info("Seeding {} companies...", n_companies)

    raw_companies = generate_companies(n_companies)
    company_objects = []
    for raw in tqdm(raw_companies, desc="Companies"):
        c = Company(**raw)
        session.add(c)
        company_objects.append(c)
    await session.flush()

    # Map company to contacts
    company_dicts = [{**c.to_dict(), "id": c.id} for c in company_objects]
    raw_contacts = generate_contacts_for_companies(company_dicts)

    contacts_by_company = {}
    contact_objects = []
    for raw in tqdm(raw_contacts, desc="Contacts"):
        ct = Contact(**raw)
        session.add(ct)
        contact_objects.append(ct)
    await session.flush()

    for ct in contact_objects:
        cid = ct.company_id
        if cid not in contacts_by_company:
            contacts_by_company[cid] = []
        contacts_by_company[cid].append({"id": ct.id})

    logger.info("Companies: {} | Contacts: {}", len(company_objects), len(contact_objects))
    return company_dicts, contacts_by_company


async def seed_communications(session, companies: list, contacts_by_company: dict):
    """Seed emails, meetings, calls, tickets, contracts."""
    logger.info("Seeding communications...")

    # Emails
    raw_emails = generate_emails_for_companies(companies, contacts_by_company)
    for raw in tqdm(raw_emails, desc="Emails"):
        session.add(Email(**{k: v for k, v in raw.items() if k != "user_id"}))
    await session.flush()

    # Meetings, calls, tickets, contracts
    comms = generate_all_communications(companies, contacts_by_company)

    for raw in tqdm(comms["meetings"], desc="Meetings"):
        session.add(Meeting(**raw))
    await session.flush()

    for raw in tqdm(comms["calls"], desc="Calls"):
        session.add(CallTranscript(**raw))
    await session.flush()

    for raw in tqdm(comms["tickets"], desc="Tickets"):
        session.add(SupportTicket(**raw))
    await session.flush()

    for raw in tqdm(comms["contracts"], desc="Contracts"):
        session.add(Contract(**raw))
    await session.flush()

    logger.info("Communications seeded | emails={} meetings={} calls={} tickets={} contracts={}",
                len(raw_emails), len(comms["meetings"]), len(comms["calls"]),
                len(comms["tickets"]), len(comms["contracts"]))


async def seed_health_snapshots(session, companies: list):
    """Generate 6 months of weekly health snapshots per company."""
    logger.info("Seeding health snapshots...")
    count = 0
    for c in companies:
        base_health = float(c.get("health_score", 70))
        for week in range(26):  # 6 months
            snap_date = datetime.utcnow() - timedelta(weeks=26 - week)
            # Add some trend drift
            noise = random.gauss(0, 3)
            health = max(5, min(100, base_health + noise + (week * 0.1 if base_health > 60 else -week * 0.2)))
            churn = round(max(0.01, min(0.99, 1 - health / 100 + random.gauss(0, 0.05))), 4)

            snap = HealthSnapshot(
                company_id=c["id"],
                health_score=round(health, 2),
                churn_risk=churn,
                sentiment_avg=round(random.gauss(0.05, 0.2), 4),
                ticket_count=random.randint(0, 15),
                engagement_rate=round(random.uniform(0.2, 0.9), 4),
                snapshot_date=snap_date,
            )
            session.add(snap)
            count += 1
    await session.flush()
    logger.info("Health snapshots seeded: {}", count)


async def seed_kg_entities(session, companies: list):
    """Seed basic knowledge graph entities from companies."""
    logger.info("Seeding knowledge graph...")
    entities = {}

    topics = ["contract renewal", "support escalation", "API integration", "pricing negotiation",
              "product roadmap", "churn risk", "expansion opportunity", "executive alignment"]

    for c in companies[:20]:  # KG for first 20 companies
        e = KGEntity(entity_type="company", name=c["name"], properties={"industry": c.get("industry")})
        session.add(e)
        await session.flush()
        entities[c["name"]] = e.id

        # Add topic connections
        for topic in random.sample(topics, k=2):
            if topic not in entities:
                te = KGEntity(entity_type="topic", name=topic)
                session.add(te)
                await session.flush()
                entities[topic] = te.id
            rel = KGRelationship(
                source_entity=e.id,
                target_entity=entities[topic],
                relation_type="discussed",
                weight=round(random.uniform(0.5, 1.0), 2),
            )
            session.add(rel)

    await session.flush()
    logger.info("KG entities seeded")


async def main():
    logger.info("+------------------------------------------+")
    logger.info("|  ClientIQ - Master Data Seeder           |")
    logger.info("+------------------------------------------+")

    try:
        async with get_db_session() as session:
            existing_companies = await session.scalar(select(func.count(Company.id)))
            if existing_companies:
                logger.info("Seed data already present: {} companies found. Skipping ingestion.", existing_companies)
                return

            await seed_roles_and_users(session)
            companies, contacts_by_company = await seed_companies_and_contacts(session, n_companies=50)
            await seed_communications(session, companies, contacts_by_company)
            await seed_health_snapshots(session, companies)
            await seed_kg_entities(session, companies)

        logger.info("+------------------------------------------+")
        logger.info("|  Seeding Complete!                       |")
        logger.info("+------------------------------------------+")
        print("\nDemo credentials:")
        print("  Admin:   admin@clientiq.demo / admin123")
        print("  Manager: manager@clientiq.demo / manager123")
        print("  Analyst: analyst@clientiq.demo / analyst123")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
