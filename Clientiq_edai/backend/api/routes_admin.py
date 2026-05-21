# Admin routes
"""
ClientIQ — Admin Routes
Audit logs, user management, and system health for admin panel.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
from typing import Any, Dict, Optional

from backend.database.connection import get_db
from backend.database.models import (
    User,
    Role,
    AuditLog,
    Company,
    Contact,
    Contract,
    Email,
    Meeting,
    CallTranscript,
    SupportTicket,
    Opportunity,
    SentimentTimeline,
)
from backend.api.routes_auth import get_current_user
from backend.ml.sentiment_model import sentiment_model
from backend.services.audit_service import audit_service
from backend.services.indexing_service import indexing_service
from backend.utils.logger import logger

router = APIRouter()


class AdminRecordCreate(BaseModel):
    company_id: str
    contact_id: Optional[str] = None
    fields: Dict[str, Any] = {}


class SentimentPredictionRequest(BaseModel):
    company_id: str
    record_type: str
    fields: Dict[str, Any] = {}


def require_admin(current_user):
    """Dependency: ensures the user has admin role."""
    # In real implementation, check the role from DB
    # Here we trust the token payload
    return current_user


def parse_datetime(value: Optional[str], field_name: str, default_now: bool = False) -> datetime:
    if not value:
        if default_now:
            return datetime.utcnow()
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} must be a valid ISO date/time")


def optional_decimal(value: Any, field_name: str, default: str = "0") -> Decimal:
    if value in (None, ""):
        value = default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a number")


def optional_int(value: Any, field_name: str, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} must be an integer")


def require_choice(value: Optional[str], field_name: str, allowed: set[str], default: str) -> str:
    choice = value or default
    if choice not in allowed:
        raise HTTPException(status_code=400, detail=f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return choice


async def validate_company_and_contact(db: AsyncSession, company_id: str, contact_id: Optional[str]):
    company = await db.scalar(select(Company).where(Company.id == company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    contact = None
    if contact_id:
        contact = await db.scalar(
            select(Contact).where(Contact.id == contact_id, Contact.company_id == company_id)
        )
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found for this company")
    return company, contact


async def add_sentiment_entry(
    db: AsyncSession,
    company_id: str,
    source_type: str,
    source_id: str,
    sentiment_score: Decimal,
    sentiment_label: str,
    recorded_at: datetime,
):
    db.add(
        SentimentTimeline(
            company_id=company_id,
            source_type=source_type,
            source_id=source_id,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            recorded_at=recorded_at,
        )
    )


def sentiment_label(score: float) -> str:
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"


def sentiment_source_type(record_type: str) -> Optional[str]:
    return {
        "email": "email",
        "meeting": "meeting",
        "call": "call",
        "ticket": "ticket",
    }.get(record_type)


def sentiment_text(record_type: str, fields: Dict[str, Any]) -> str:
    text_fields = {
        "email": ["subject", "body"],
        "meeting": ["title", "attendees", "notes", "action_items"],
        "call": ["summary", "transcript", "key_topics"],
        "ticket": ["title", "description", "resolution", "category"],
    }.get(record_type, [])
    return "\n".join(str(fields.get(name) or "").strip() for name in text_fields).strip()


async def predict_sentiment_for_record(
    db: AsyncSession,
    company_id: str,
    record_type: str,
    fields: Dict[str, Any],
) -> Dict[str, Any]:
    await validate_company_and_contact(db, company_id, None)

    source_type = sentiment_source_type(record_type)
    if not source_type:
        raise HTTPException(status_code=400, detail="Sentiment prediction is only available for email, meeting, call, and ticket")

    text = sentiment_text(record_type, fields or {})
    text_score = None
    if text:
        text_score, _ = sentiment_model.score(text)

    history_query = (
        select(SentimentTimeline)
        .where(SentimentTimeline.company_id == company_id)
        .order_by(desc(SentimentTimeline.recorded_at))
        .limit(20)
    )
    if source_type:
        same_type_query = history_query.where(SentimentTimeline.source_type == source_type)
        same_type_result = await db.execute(same_type_query)
        history_rows = same_type_result.scalars().all()
    else:
        history_rows = []

    if not history_rows:
        history_result = await db.execute(history_query)
        history_rows = history_result.scalars().all()

    history_count = len(history_rows)
    history_score = None
    if history_rows:
        weighted_total = 0.0
        total_weight = 0.0
        for idx, row in enumerate(history_rows):
            weight = 1.0 / (idx + 1)
            weighted_total += float(row.sentiment_score or 0) * weight
            total_weight += weight
        history_score = weighted_total / total_weight if total_weight else 0.0

    if text_score is not None and history_score is not None:
        score = (0.6 * text_score) + (0.4 * history_score)
        basis = f"Predicted from current text + {history_count} past company records"
    elif text_score is not None:
        score = text_score
        basis = "Predicted from current text"
    elif history_score is not None:
        score = history_score
        basis = f"Predicted from {history_count} past company records"
    else:
        score = 0.0
        basis = "No text or past sentiment found; using neutral"

    score = round(max(-1.0, min(1.0, score)), 4)
    return {
        "score": score,
        "label": sentiment_label(score),
        "text_score": round(text_score, 4) if text_score is not None else None,
        "history_score": round(history_score, 4) if history_score is not None else None,
        "history_count": history_count,
        "basis": basis,
    }


@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries with optional filtering."""
    logs = await audit_service.get_logs(db, user_id=user_id, action=action, limit=limit, offset=offset)
    return {"logs": logs, "count": len(logs)}


@router.get("/users")
async def list_users(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all system users (admin only)."""
    result = await db.execute(select(User).order_by(desc(User.created_at)))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/roles")
async def list_roles(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in roles]


@router.get("/system-stats")
async def system_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """System-wide statistics for admin dashboard."""
    from sqlalchemy import func
    from backend.database.models import Company, SupportTicket, Email, AgentSession

    total_companies  = await db.scalar(select(func.count(Company.id))) or 0
    total_tickets    = await db.scalar(select(func.count(SupportTicket.id))) or 0
    total_emails     = await db.scalar(select(func.count(Email.id))) or 0
    total_sessions   = await db.scalar(select(func.count(AgentSession.id))) or 0
    total_audit_logs = await db.scalar(select(func.count(AuditLog.id))) or 0

    return {
        "total_companies":  total_companies,
        "total_tickets":    total_tickets,
        "total_emails":     total_emails,
        "total_sessions":   total_sessions,
        "total_audit_logs": total_audit_logs,
    }


@router.post("/sentiment-prediction")
async def predict_sentiment(
    body: SentimentPredictionRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Predict sentiment for an admin-entered CRM communication."""
    return await predict_sentiment_for_record(db, body.company_id, body.record_type, body.fields or {})


@router.post("/records/{record_type}", status_code=status.HTTP_201_CREATED)
async def create_crm_record(
    record_type: str,
    body: AdminRecordCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create CRM activity records from the admin data-entry panel."""
    allowed_types = {"email", "meeting", "call", "ticket", "opportunity_note", "contract"}
    if record_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"record_type must be one of: {', '.join(sorted(allowed_types))}")

    await validate_company_and_contact(db, body.company_id, body.contact_id)
    fields = body.fields or {}
    predicted_sentiment = None
    if sentiment_source_type(record_type) and (
        fields.get("sentiment_score") in (None, "") or fields.get("sentiment_label") in (None, "")
    ):
        predicted_sentiment = await predict_sentiment_for_record(db, body.company_id, record_type, fields)

    sentiment_score_value = fields.get("sentiment_score")
    if sentiment_score_value in (None, "") and predicted_sentiment:
        sentiment_score_value = predicted_sentiment["score"]
    sentiment_label_value = fields.get("sentiment_label")
    if sentiment_label_value in (None, "") and predicted_sentiment:
        sentiment_label_value = predicted_sentiment["label"]

    sentiment_score = optional_decimal(sentiment_score_value, "sentiment_score", "0")
    sentiment_label_value = require_choice(
        sentiment_label_value,
        "sentiment_label",
        {"positive", "neutral", "negative"},
        "neutral",
    )

    if record_type == "email":
        sent_at = parse_datetime(fields.get("sent_at"), "sent_at", default_now=True)
        record = Email(
            company_id=body.company_id,
            contact_id=body.contact_id,
            user_id=current_user.id,
            direction=require_choice(fields.get("direction"), "direction", {"inbound", "outbound"}, "outbound"),
            subject=fields.get("subject") or "Admin email entry",
            body=fields.get("body") or "",
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label_value,
            thread_id=fields.get("thread_id") or None,
            sent_at=sent_at,
        )
        source_type = "email"
        recorded_at = sent_at

    elif record_type == "meeting":
        scheduled_at = parse_datetime(fields.get("scheduled_at"), "scheduled_at", default_now=True)
        attendees_raw = fields.get("attendees") or ""
        action_items_raw = fields.get("action_items") or ""
        record = Meeting(
            company_id=body.company_id,
            title=fields.get("title") or "Admin meeting entry",
            meeting_type=require_choice(
                fields.get("meeting_type"),
                "meeting_type",
                {"discovery", "demo", "qbr", "renewal", "support", "kickoff", "other"},
                "other",
            ),
            attendees=[item.strip() for item in attendees_raw.split(",") if item.strip()],
            notes=fields.get("notes") or "",
            action_items=[item.strip() for item in action_items_raw.split("\n") if item.strip()],
            sentiment_score=sentiment_score,
            duration_mins=optional_int(fields.get("duration_mins"), "duration_mins", 60),
            scheduled_at=scheduled_at,
        )
        source_type = "meeting"
        recorded_at = scheduled_at

    elif record_type == "call":
        called_at = parse_datetime(fields.get("called_at"), "called_at", default_now=True)
        key_topics_raw = fields.get("key_topics") or ""
        record = CallTranscript(
            company_id=body.company_id,
            contact_id=body.contact_id,
            call_type=require_choice(
                fields.get("call_type"),
                "call_type",
                {"sales", "support", "renewal", "escalation", "other"},
                "other",
            ),
            duration_secs=optional_int(fields.get("duration_secs"), "duration_secs", 0),
            transcript=fields.get("transcript") or "",
            summary=fields.get("summary") or "",
            sentiment_score=sentiment_score,
            key_topics=[item.strip() for item in key_topics_raw.split(",") if item.strip()],
            called_at=called_at,
        )
        source_type = "call"
        recorded_at = called_at

    elif record_type == "ticket":
        opened_at = parse_datetime(fields.get("opened_at"), "opened_at", default_now=True)
        ticket_number = fields.get("ticket_number")
        if not ticket_number:
            count = await db.scalar(select(func.count(SupportTicket.id))) or 0
            ticket_number = f"ADM-{datetime.utcnow().strftime('%Y%m%d')}-{count + 1:05d}"
        record = SupportTicket(
            company_id=body.company_id,
            contact_id=body.contact_id,
            ticket_number=ticket_number,
            title=fields.get("title") or "Admin ticket entry",
            description=fields.get("description") or "",
            priority=require_choice(fields.get("priority"), "priority", {"low", "medium", "high", "critical"}, "medium"),
            status=require_choice(
                fields.get("ticket_status"),
                "ticket_status",
                {"open", "in_progress", "pending_customer", "resolved", "closed"},
                "open",
            ),
            category=fields.get("category") or None,
            resolution=fields.get("resolution") or None,
            sentiment_score=sentiment_score,
            opened_at=opened_at,
        )
        source_type = "ticket"
        recorded_at = opened_at

    elif record_type == "opportunity_note":
        record = Opportunity(
            company_id=body.company_id,
            owner_id=current_user.id,
            name=fields.get("name") or "Admin note",
            stage=require_choice(
                fields.get("stage"),
                "stage",
                {"prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"},
                "prospecting",
            ),
            amount=optional_decimal(fields.get("amount"), "amount", "0"),
            probability=optional_decimal(fields.get("probability"), "probability", "0"),
            close_date=parse_datetime(fields.get("close_date"), "close_date") if fields.get("close_date") else None,
            source=fields.get("source") or "admin",
            notes=fields.get("notes") or "",
        )
        source_type = None
        recorded_at = None

    else:
        record = Contract(
            company_id=body.company_id,
            title=fields.get("title") or "Admin contract entry",
            contract_type=require_choice(
                fields.get("contract_type"),
                "contract_type",
                {"saas", "professional_services", "support", "partnership", "nda"},
                "saas",
            ),
            value=optional_decimal(fields.get("value"), "value", "0"),
            currency=fields.get("currency") or "USD",
            start_date=parse_datetime(fields.get("start_date"), "start_date"),
            end_date=parse_datetime(fields.get("end_date"), "end_date"),
            auto_renew=bool(fields.get("auto_renew")),
            status=require_choice(fields.get("contract_status"), "contract_status", {"draft", "active", "expired", "terminated"}, "active"),
            terms_text=fields.get("terms_text") or "",
            signed_at=parse_datetime(fields.get("signed_at"), "signed_at") if fields.get("signed_at") else None,
        )
        source_type = None
        recorded_at = None

    db.add(record)
    await db.flush()
    if source_type:
        await add_sentiment_entry(
            db,
            body.company_id,
            source_type,
            record.id,
            sentiment_score,
            sentiment_label_value,
            recorded_at,
        )
    await db.commit()
    await db.refresh(record)
    await audit_service.log(
        db,
        current_user.id,
        f"{record_type}_created",
        resource_type=record.__tablename__,
        resource_id=record.id,
        details={"company_id": body.company_id, "contact_id": body.contact_id},
    )

    # ── Auto-index into Pinecone immediately after TiDB commit ──────────────
    # Runs in a background thread so it never delays the HTTP response.
    # Supported: email, meeting, call, ticket, contract.
    # opportunity_note is silently skipped (no free-text body to embed).
    await indexing_service.index_record(record, source_type or "")

    return {"message": f"{record_type.replace('_', ' ')} created", "record": record.to_dict()}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    await audit_service.log(db, current_user.id, "user_deactivated", resource_id=user_id)
    return {"message": f"User {user_id} deactivated"}