import logging
import re
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from redis.asyncio import Redis
from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.session import get_sessionmaker
from backend.app.models.enums import UserRole
from backend.app.models.organization import Customer, User
from backend.app.services.keycloak_admin import KeycloakAdminService
from backend.app.services.rate_limit import RateLimitExceeded, check_rate_limit

log = logging.getLogger("aria.onboarding")
router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    company_name: str


class RegisterResponse(BaseModel):
    success: bool
    workspace_id: str
    message: str


def sluggify(text: str) -> str:
    """Convert text to a valid URL slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


@router.post("/register", response_model=RegisterResponse)
async def register_account(body: RegisterRequest, request: Request):
    """Register a new customer/workspace and admin user."""

    # Anti-abuse: rate-limit public self-registration by client IP (5 / hour).
    client_ip = request.client.host if request.client else "unknown"
    redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        await check_rate_limit(redis, f"register:{client_ip}", limit=5, window=3600)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message
        ) from exc
    finally:
        await redis.aclose()

    workspace_slug = sluggify(body.company_name)
    if not workspace_slug:
        raise HTTPException(status_code=400, detail="Invalid company name")

    sessionmaker = get_sessionmaker()
    kc_service = KeycloakAdminService()

    try:
        async with sessionmaker() as session:
            # 1. Check if workspace exists
            existing_cust = (
                await session.execute(select(Customer).where(Customer.slug == workspace_slug))
            ).scalar_one_or_none()

            if existing_cust:
                # Add random suffix to ensure uniqueness
                workspace_slug = f"{workspace_slug}-{str(uuid.uuid4())[:4]}"

            # 2. Check if email exists in DB (Keycloak will also check, but we check here too)
            existing_user = (
                await session.execute(select(User).where(User.email == body.email))
            ).scalar_one_or_none()

            if existing_user:
                raise HTTPException(status_code=409, detail="Email already registered")

            # 3. Create the Customer in DB
            new_customer = Customer(
                name=body.company_name, slug=workspace_slug, plan="free", is_active=True
            )
            session.add(new_customer)
            await session.flush()  # Get customer.id

            # 4. Create user in Keycloak (as admin for this workspace)
            # This might raise HTTPException(409) if it exists in KC
            kc_user_id, db_user_id = await kc_service.create_user(
                email=body.email,
                display_name=body.name,
                password=body.password,
                role="admin",
                workspace_id=workspace_slug,
                temporary=False,  # self-registration: the user chose this password
            )

            # 5. Create the User in DB
            new_user = User(
                id=uuid.UUID(db_user_id),
                external_id=kc_user_id,
                customer_id=new_customer.id,
                email=body.email,
                display_name=body.name,
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(new_user)

            await session.commit()

            return RegisterResponse(
                success=True, workspace_id=workspace_slug, message="Registration successful"
            )

    except HTTPException:
        raise
    except Exception as exc:
        log.error(f"Registration failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
