# Compliance auditing
"""
ClientIQ — Audit Service
Records all user actions for compliance and governance tracking.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database.models import AuditLog
from backend.utils.logger import logger


IST = ZoneInfo("Asia/Kolkata")


def to_ist_iso(value: datetime) -> str:
    """Convert stored UTC timestamps to explicit IST ISO strings."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(IST).isoformat()


class AuditService:
    async def log(
        self,
        db: AsyncSession,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        await db.commit()
        logger.info("[Audit] {} | user={} | status={}", action, user_id, status)
        return entry

    async def get_logs(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        q = select(AuditLog).order_by(desc(AuditLog.created_at))
        if user_id:
            q = q.where(AuditLog.user_id == user_id)
        if action:
            q = q.where(AuditLog.action == action)
        q = q.limit(limit).offset(offset)
        result = await db.execute(q)
        logs = []
        for row in result.scalars().all():
            item = row.to_dict()
            if row.created_at:
                item["created_at"] = to_ist_iso(row.created_at)
            logs.append(item)
        return logs


audit_service = AuditService()
