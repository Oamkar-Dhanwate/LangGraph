# ORM models
"""
ClientIQ — SQLAlchemy ORM Models
Mirrors the TiDB schema with full relationship mappings.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, JSON, Numeric, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base model with common utilities."""

    def to_dict(self) -> dict:
        """Serialize model to plain dictionary."""
        result = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            result[col.name] = val
        return result


def new_uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# RBAC
# ─────────────────────────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id          = Column(String(36), primary_key=True, default=new_uuid)
    name        = Column(String(50), nullable=False, unique=True)
    permissions = Column(JSON, nullable=False, default=dict)
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    users: Mapped[List["User"]] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    email           = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(255), nullable=False)
    role_id         = Column(String(36), ForeignKey("roles.id"), nullable=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    last_login      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)

    role:     Mapped["Role"]           = relationship("Role", back_populates="users")
    sessions: Mapped[List["AgentSession"]] = relationship("AgentSession", back_populates="user")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")


# ─────────────────────────────────────────────────────────────────────────────
# CRM
# ─────────────────────────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id            = Column(String(36), primary_key=True, default=new_uuid)
    name          = Column(String(255), nullable=False)
    industry      = Column(String(100))
    size_category = Column(Enum("startup", "smb", "mid_market", "enterprise"), default="smb")
    annual_revenue = Column(Numeric(15, 2))
    country       = Column(String(100), default="United States")
    website       = Column(String(255))
    account_tier  = Column(Enum("bronze", "silver", "gold", "platinum"), default="silver")
    health_score  = Column(Numeric(5, 2), default=70.00)
    churn_risk    = Column(Numeric(5, 4), default=0.10)
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at    = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    contacts:   Mapped[List["Contact"]]        = relationship("Contact", back_populates="company", cascade="all, delete")
    contracts:  Mapped[List["Contract"]]       = relationship("Contract", back_populates="company")
    emails:     Mapped[List["Email"]]          = relationship("Email", back_populates="company")
    meetings:   Mapped[List["Meeting"]]        = relationship("Meeting", back_populates="company")
    calls:      Mapped[List["CallTranscript"]] = relationship("CallTranscript", back_populates="company")
    tickets:    Mapped[List["SupportTicket"]]  = relationship("SupportTicket", back_populates="company")
    health_snaps: Mapped[List["HealthSnapshot"]] = relationship("HealthSnapshot", back_populates="company")
    sentiment_timeline: Mapped[List["SentimentTimeline"]] = relationship("SentimentTimeline", back_populates="company")
    opportunities: Mapped[List["Opportunity"]] = relationship("Opportunity", back_populates="company")


class Contact(Base):
    __tablename__ = "contacts"

    id             = Column(String(36), primary_key=True, default=new_uuid)
    company_id     = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    first_name     = Column(String(100), nullable=False)
    last_name      = Column(String(100), nullable=False)
    email          = Column(String(255), nullable=False)
    phone          = Column(String(50))
    job_title      = Column(String(150))
    department     = Column(String(100))
    is_primary     = Column(Boolean, default=False)
    sentiment_score = Column(Numeric(5, 4), default=0.0)
    last_contacted = Column(DateTime)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)

    company: Mapped["Company"] = relationship("Company", back_populates="contacts")


# ─────────────────────────────────────────────────────────────────────────────
# Sales
# ─────────────────────────────────────────────────────────────────────────────

class Opportunity(Base):
    __tablename__ = "opportunities"

    id          = Column(String(36), primary_key=True, default=new_uuid)
    company_id  = Column(String(36), ForeignKey("companies.id"), nullable=False)
    owner_id    = Column(String(36), ForeignKey("users.id"))
    name        = Column(String(255), nullable=False)
    stage       = Column(Enum("prospecting","qualification","proposal","negotiation","closed_won","closed_lost"), default="prospecting")
    amount      = Column(Numeric(15, 2), default=0)
    probability = Column(Numeric(5, 2), default=0)
    close_date  = Column(DateTime)
    source      = Column(String(100))
    notes       = Column(Text)
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company:   Mapped["Company"] = relationship("Company", back_populates="opportunities")
    contracts: Mapped[List["Contract"]] = relationship("Contract", back_populates="opportunity")


class Contract(Base):
    __tablename__ = "contracts"

    id             = Column(String(36), primary_key=True, default=new_uuid)
    company_id     = Column(String(36), ForeignKey("companies.id"), nullable=False)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"))
    title          = Column(String(255), nullable=False)
    contract_type  = Column(Enum("saas","professional_services","support","partnership","nda"), default="saas")
    value          = Column(Numeric(15, 2), nullable=False)
    currency       = Column(String(10), default="USD")
    start_date     = Column(DateTime, nullable=False)
    end_date       = Column(DateTime, nullable=False)
    auto_renew     = Column(Boolean, default=False)
    status         = Column(Enum("draft","active","expired","terminated"), default="active")
    terms_text     = Column(Text)
    signed_at      = Column(DateTime)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)

    company:     Mapped["Company"]     = relationship("Company", back_populates="contracts")
    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="contracts")


# ─────────────────────────────────────────────────────────────────────────────
# Communications
# ─────────────────────────────────────────────────────────────────────────────

class Email(Base):
    __tablename__ = "emails"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    company_id      = Column(String(36), ForeignKey("companies.id"), nullable=False)
    contact_id      = Column(String(36), ForeignKey("contacts.id"))
    user_id         = Column(String(36), ForeignKey("users.id"))
    direction       = Column(Enum("inbound","outbound"), default="outbound")
    subject         = Column(String(500), nullable=False)
    body            = Column(Text, nullable=False)
    sentiment_score = Column(Numeric(5, 4), default=0.0)
    sentiment_label = Column(Enum("positive","neutral","negative"), default="neutral")
    thread_id       = Column(String(36))
    sent_at         = Column(DateTime, nullable=False, default=datetime.utcnow)

    company: Mapped["Company"] = relationship("Company", back_populates="emails")
    contact: Mapped[Optional["Contact"]] = relationship("Contact")


class Meeting(Base):
    __tablename__ = "meetings"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    company_id      = Column(String(36), ForeignKey("companies.id"), nullable=False)
    title           = Column(String(255), nullable=False)
    meeting_type    = Column(Enum("discovery","demo","qbr","renewal","support","kickoff","other"), default="other")
    attendees       = Column(JSON)
    notes           = Column(Text)
    action_items    = Column(JSON)
    sentiment_score = Column(Numeric(5, 4), default=0.0)
    duration_mins   = Column(Integer, default=60)
    scheduled_at    = Column(DateTime, nullable=False)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)

    company: Mapped["Company"] = relationship("Company", back_populates="meetings")


class CallTranscript(Base):
    __tablename__ = "call_transcripts"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    company_id      = Column(String(36), ForeignKey("companies.id"), nullable=False)
    contact_id      = Column(String(36), ForeignKey("contacts.id"))
    call_type       = Column(Enum("sales","support","renewal","escalation","other"), default="other")
    duration_secs   = Column(Integer, default=0)
    transcript      = Column(Text, nullable=False)
    summary         = Column(Text)
    sentiment_score = Column(Numeric(5, 4), default=0.0)
    key_topics      = Column(JSON)
    called_at       = Column(DateTime, nullable=False)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)

    company: Mapped["Company"] = relationship("Company", back_populates="calls")
    contact: Mapped[Optional["Contact"]] = relationship("Contact")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id                = Column(String(36), primary_key=True, default=new_uuid)
    company_id        = Column(String(36), ForeignKey("companies.id"), nullable=False)
    contact_id        = Column(String(36), ForeignKey("contacts.id"))
    ticket_number     = Column(String(50), nullable=False, unique=True)
    title             = Column(String(500), nullable=False)
    description       = Column(Text, nullable=False)
    priority          = Column(Enum("low","medium","high","critical"), default="medium")
    status            = Column(Enum("open","in_progress","pending_customer","resolved","closed"), default="open")
    category          = Column(String(100))
    resolution        = Column(Text)
    sentiment_score   = Column(Numeric(5, 4), default=0.0)
    first_response_hrs = Column(Integer)
    resolution_hrs    = Column(Integer)
    opened_at         = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at       = Column(DateTime)

    company: Mapped["Company"] = relationship("Company", back_populates="tickets")
    contact: Mapped[Optional["Contact"]] = relationship("Contact")


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────

class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    company_id      = Column(String(36), ForeignKey("companies.id"), nullable=False)
    health_score    = Column(Numeric(5, 2), nullable=False)
    churn_risk      = Column(Numeric(5, 4), nullable=False)
    sentiment_avg   = Column(Numeric(5, 4))
    ticket_count    = Column(Integer, default=0)
    engagement_rate = Column(Numeric(5, 4), default=0)
    snapshot_date   = Column(DateTime, nullable=False)
    computed_at     = Column(DateTime, nullable=False, default=datetime.utcnow)

    company: Mapped["Company"] = relationship("Company", back_populates="health_snaps")


class SentimentTimeline(Base):
    __tablename__ = "sentiment_timeline"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    company_id      = Column(String(36), ForeignKey("companies.id"), nullable=False)
    source_type     = Column(Enum("email", "meeting", "call", "ticket"), nullable=False)
    source_id       = Column(String(36), nullable=False)
    sentiment_score = Column(Numeric(5, 4), nullable=False)
    sentiment_label = Column(Enum("positive", "neutral", "negative"), nullable=False)
    recorded_at     = Column(DateTime, nullable=False)

    company: Mapped["Company"] = relationship("Company", back_populates="sentiment_timeline")


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Graph
# ─────────────────────────────────────────────────────────────────────────────

class KGEntity(Base):
    __tablename__ = "kg_entities"

    id          = Column(String(36), primary_key=True, default=new_uuid)
    entity_type = Column(Enum("company","contact","product","topic","event","risk"), nullable=False)
    name        = Column(String(255), nullable=False)
    properties  = Column(JSON)
    source_id   = Column(String(36))
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)


class KGRelationship(Base):
    __tablename__ = "kg_relationships"

    id            = Column(String(36), primary_key=True, default=new_uuid)
    source_entity = Column(String(36), ForeignKey("kg_entities.id"), nullable=False)
    target_entity = Column(String(36), ForeignKey("kg_entities.id"), nullable=False)
    relation_type = Column(String(100), nullable=False)
    weight        = Column(Numeric(5, 4), default=1.0)
    properties    = Column(JSON)
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Audit & Sessions
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id            = Column(String(36), primary_key=True, default=new_uuid)
    user_id       = Column(String(36), ForeignKey("users.id"))
    action        = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id   = Column(String(36))
    details       = Column(JSON)
    ip_address    = Column(String(45))
    user_agent    = Column(String(500))
    status        = Column(Enum("success","failure","blocked"), default="success")
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id            = Column(String(36), primary_key=True, default=new_uuid)
    user_id       = Column(String(36), ForeignKey("users.id"))
    session_token = Column(String(255), nullable=False, unique=True)
    conversation  = Column(JSON, nullable=False, default=list)
    context       = Column(JSON)
    total_tokens  = Column(Integer, default=0)
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_active   = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="sessions")
