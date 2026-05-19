# Client routes
"""
ClientIQ — Client Routes
Company profiles, contact lists, meeting history, contracts, tickets.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional

from backend.database.connection import get_db
from backend.database.models import Company, Contact, Meeting, Contract, SupportTicket, Email, CallTranscript
from backend.api.routes_auth import get_current_user

router = APIRouter()


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