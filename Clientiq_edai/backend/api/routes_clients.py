# Client routes
"""
ClientIQ — Client Routes
Company profiles, contact lists, meeting history, contracts, tickets.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database.connection import get_db
from backend.database.models import Company, Contact, Meeting, Contract, SupportTicket, Email, CallTranscript
from backend.api.routes_auth import get_current_user
from backend.services.audit_service import audit_service
from backend.services.graph_service import graph_service

router = APIRouter()


class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    size_category: Optional[str] = "smb"
    annual_revenue: Optional[Decimal] = None
    country: Optional[str] = "United States"
    website: Optional[str] = None
    account_tier: Optional[str] = "silver"
    health_score: Optional[Decimal] = Decimal("70.00")
    churn_risk: Optional[Decimal] = Decimal("0.10")


def validate_choice(value: Optional[str], field_name: str, allowed: set[str], default: str) -> str:
    choice = value or default
    if choice not in allowed:
        raise HTTPException(status_code=400, detail=f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return choice


def validate_decimal_range(
    value: Optional[Decimal],
    field_name: str,
    default: Decimal,
    min_value: Decimal,
    max_value: Decimal,
) -> Decimal:
    if value is None:
        value = default
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a number")
    if value < min_value or value > max_value:
        raise HTTPException(status_code=400, detail=f"{field_name} must be between {min_value} and {max_value}")
    return value


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_client(
    body: CompanyCreate,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new CRM company/client."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = await db.scalar(select(Company).where(Company.name == name))
    if existing:
        raise HTTPException(status_code=409, detail="Company already exists")

    company = Company(
        name=name,
        industry=body.industry,
        size_category=validate_choice(
            body.size_category,
            "size_category",
            {"startup", "smb", "mid_market", "enterprise"},
            "smb",
        ),
        annual_revenue=body.annual_revenue,
        country=body.country or "United States",
        website=body.website,
        account_tier=validate_choice(
            body.account_tier,
            "account_tier",
            {"bronze", "silver", "gold", "platinum"},
            "silver",
        ),
        health_score=validate_decimal_range(
            body.health_score,
            "health_score",
            Decimal("70.00"),
            Decimal("0"),
            Decimal("100"),
        ),
        churn_risk=validate_decimal_range(
            body.churn_risk,
            "churn_risk",
            Decimal("0.10"),
            Decimal("0"),
            Decimal("1"),
        ),
    )
    db.add(company)
    await db.flush()
    await graph_service.upsert_company(db, company)
    await db.commit()
    await db.refresh(company)

    await audit_service.log(
        db,
        current_user.id,
        "company_created",
        resource_type="companies",
        resource_id=company.id,
        details={"name": company.name, "account_tier": company.account_tier},
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Company created", "company": company.to_dict()}


@router.get("/")
async def list_clients(
    search: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all clients with optional search/filter."""
    q = select(Company).order_by(desc(Company.health_score))
    if search:
        q = q.where(Company.name.ilike(f"%{search}%"))
    if tier:
        q = q.where(Company.account_tier == tier)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    companies = result.scalars().all()
    return [c.to_dict() for c in companies]


@router.get("/{company_id}")
async def get_client(
    company_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full company profile."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company.to_dict()


@router.get("/{company_id}/contacts")
async def get_contacts(
    company_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Contact).where(Contact.company_id == company_id))
    return [c.to_dict() for c in result.scalars().all()]


@router.get("/{company_id}/meetings")
async def get_meetings(
    company_id: str,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Meeting).where(Meeting.company_id == company_id)
        .order_by(desc(Meeting.scheduled_at)).limit(limit)
    )
    return [m.to_dict() for m in result.scalars().all()]


@router.get("/{company_id}/contracts")
async def get_contracts(
    company_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Contract).where(Contract.company_id == company_id))
    return [c.to_dict() for c in result.scalars().all()]


@router.get("/{company_id}/tickets")
async def get_tickets(
    company_id: str,
    status: Optional[str] = None,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(SupportTicket).where(SupportTicket.company_id == company_id).order_by(desc(SupportTicket.opened_at)).limit(limit)
    if status:
        q = q.where(SupportTicket.status == status)
    result = await db.execute(q)
    return [t.to_dict() for t in result.scalars().all()]


@router.get("/{company_id}/emails")
async def get_emails(
    company_id: str,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Email).where(Email.company_id == company_id)
        .order_by(desc(Email.sent_at)).limit(limit)
    )
    return [e.to_dict() for e in result.scalars().all()]


@router.get("/{company_id}/calls")
async def get_calls(
    company_id: str,
    limit: int = 10,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CallTranscript).where(CallTranscript.company_id == company_id)
        .order_by(desc(CallTranscript.called_at)).limit(limit)
    )
    return [c.to_dict() for c in result.scalars().all()]
