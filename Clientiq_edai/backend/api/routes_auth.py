# Authentication routes
"""
ClientIQ — Auth Routes
Login, token refresh, user profile, and registration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from backend.database.connection import get_db
from backend.services.auth_service import auth_service
from backend.services.audit_service import audit_service
from backend.utils.logger import logger

router = APIRouter()
security = HTTPBearer()


# ─── Request / Response schemas ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "analyst"

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


# ─── Dependency: get current user ─────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    user = await auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = await auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        await audit_service.log(db, None, "login_failed", details={"email": body.email}, status="failure",
                                ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    from sqlalchemy import select
    from backend.database.models import Role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    role_name = role.name if role else "viewer"

    token = auth_service.create_access_token({"sub": user.id, "role": role_name, "email": user.email})

    await audit_service.log(db, user.id, "login_success",
                            ip_address=request.client.host if request.client else None)

    return LoginResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        role=role_name,
    )


@router.post("/register", response_model=UserProfile, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user (admin action in production)."""
    from sqlalchemy import select
    from backend.database.models import User
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await auth_service.create_user(db, body.email, body.password, body.full_name, body.role)
    return UserProfile(id=user.id, email=user.email, full_name=user.full_name, role=body.role, is_active=True)


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return current user profile."""
    from sqlalchemy import select
    from backend.database.models import Role
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalar_one_or_none()
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=role.name if role else "viewer",
        is_active=current_user.is_active,
    )


@router.post("/logout")
async def logout(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await audit_service.log(db, current_user.id, "logout")
    return {"message": "Logged out successfully"}