# JWT/RBAC auth service
"""
ClientIQ — Authentication Service
Handles JWT token generation, validation, password hashing, and RBAC.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database.models import User, Role
from backend.utils.config import settings
from backend.utils.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Handles all authentication and authorization logic."""

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def create_access_token(self, data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.app_secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError as e:
            logger.warning("[Auth] Token decode failed: {}", e)
            return None

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
        logger.info("[Auth] User authenticated: {}", email)
        return user

    async def get_current_user(self, token: str, db: AsyncSession) -> Optional[User]:
        payload = self.decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(self, db: AsyncSession, email: str, password: str, full_name: str, role_name: str = "analyst") -> User:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, permissions={})
            db.add(role)
            await db.flush()

        user = User(
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name,
            role_id=role.id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


auth_service = AuthService()