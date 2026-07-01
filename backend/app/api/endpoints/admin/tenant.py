"""Admin: tenant configuration (token quotas, row limits).

Manages system-wide limits for the workspace/tenant.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.database import CustomerDBConfig
from backend.app.models.enums import DatabaseType
from backend.app.models.organization import Customer
from backend.app.models.token import TokenQuota
from backend.app.services.crypto import async_encrypt_password
from backend.app.services.workspace_language import get_workspace_language

DEFAULT_DAILY_TOKEN_LIMIT = 50000
DEFAULT_MAX_ROW_LIMIT = 1000
DEFAULT_MAX_EXPORT_ROW_LIMIT = 100000
DEFAULT_EXPORT_BATCH_SIZE = 50000
DEFAULT_EXPORT_LINK_TTL_DAYS = 3
HARD_ROW_CEILING = 1_000_000

log = logging.getLogger("aria.admin")
router = APIRouter()


def validate_row_limit_invariant(*, max_row: int, max_export: int, batch: int) -> None:
    """Enforce 1 ≤ max_row ≤ max_export ≤ HARD_ROW_CEILING and batch ≤ max_export."""
    if not (1 <= max_row <= max_export <= HARD_ROW_CEILING):
        raise ValueError(
            "Require 1 ≤ max_row_limit ≤ max_export_row_limit ≤ 1,000,000 "
            f"(got max_row_limit={max_row}, max_export_row_limit={max_export})"
        )
    if not (1 <= batch <= max_export):
        raise ValueError(
            "Require 1 ≤ export_batch_size ≤ max_export_row_limit "
            f"(got export_batch_size={batch}, max_export_row_limit={max_export})"
        )


class DBConfigModel(BaseModel):
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str | None = None


class TenantConfigUpdate(BaseModel):
    """Update tenant configuration."""

    daily_token_limit: int | None = Field(
        default=None,
        ge=1000,
        le=10_000_000,
        description="Daily token limit per user/team (1K - 10M)",
    )
    max_row_limit: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description="Max rows rendered per query in the UI (display ceiling)",
    )
    max_export_row_limit: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description="Max rows written to a CSV export artifact (export ceiling)",
    )
    export_batch_size: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description="Rows fetched per batch when streaming an export",
    )
    export_link_ttl_days: int | None = Field(
        default=None,
        ge=1,
        description="Days an exported CSV stays downloadable before it expires",
    )
    db_config: DBConfigModel | None = None
    language: str | None = Field(
        default=None,
        pattern="^(en|tr)$",
        description="Customer response language: 'en' or 'tr' (forces all chat/insight/suggestions)",
    )

    @model_validator(mode="after")
    def _check_ordering(self) -> "TenantConfigUpdate":
        # Only validate the relationship between fields submitted together;
        # the handler does the final check against stored values.
        if (
            self.max_row_limit is not None
            and self.max_export_row_limit is not None
            and self.max_row_limit > self.max_export_row_limit
        ):
            raise ValueError("max_row_limit must be ≤ max_export_row_limit")
        if (
            self.export_batch_size is not None
            and self.max_export_row_limit is not None
            and self.export_batch_size > self.max_export_row_limit
        ):
            raise ValueError("export_batch_size must be ≤ max_export_row_limit")
        return self


class TenantConfigResponse(BaseModel):
    """Tenant configuration response."""

    daily_token_limit: int
    max_row_limit: int
    max_export_row_limit: int
    export_batch_size: int
    export_link_ttl_days: int
    source: str  # "db" or "default"
    db_config: dict | None = None
    language: str = "en"


@router.get("")
async def get_tenant_config(
    current_user: Any = Depends(get_current_user),
) -> TenantConfigResponse | dict:
    """Get tenant limits.

    Daily token limit comes from the active TokenQuota (real);
    the per-query row limit is a platform default until a per-tenant override exists.
    Degrades to defaults if the table is not yet migrated / DB is unavailable.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    quota = None
    db_config_res = None
    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    row_limit = DEFAULT_MAX_ROW_LIMIT
    export_row_limit = DEFAULT_MAX_EXPORT_ROW_LIMIT
    export_batch = DEFAULT_EXPORT_BATCH_SIZE
    export_link_ttl = DEFAULT_EXPORT_LINK_TTL_DAYS

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if customer:
                # Token quota scoped to THIS customer (no cross-tenant default leak).
                quota = (
                    await session.execute(
                        select(TokenQuota)
                        .where(
                            TokenQuota.is_active.is_(True), TokenQuota.customer_id == customer.id
                        )
                        .order_by(TokenQuota.created_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                db_config_res = (
                    await session.execute(
                        select(CustomerDBConfig).where(CustomerDBConfig.customer_id == customer.id)
                    )
                ).scalar_one_or_none()

                # Also fetch row/export limits if they exist
                if db_config_res:
                    row_limit = db_config_res.max_row_limit
                    export_row_limit = db_config_res.max_export_row_limit
                    export_batch = db_config_res.export_batch_size
                    export_link_ttl = db_config_res.export_link_ttl_days

    except SQLAlchemyError as exc:
        log.warning("admin.tenant: query failed (table not migrated?): %s", exc)

    return TenantConfigResponse(
        daily_token_limit=quota.token_limit if quota else DEFAULT_DAILY_TOKEN_LIMIT,
        max_row_limit=row_limit,
        max_export_row_limit=export_row_limit,
        export_batch_size=export_batch,
        export_link_ttl_days=export_link_ttl,
        source="db" if quota else "default",
        language=await get_workspace_language(workspace_id),
        db_config={
            "db_type": db_config_res.db_type.value
            if hasattr(db_config_res.db_type, "value")
            else str(db_config_res.db_type),
            "host": db_config_res.host,
            "port": db_config_res.port,
            "database": db_config_res.database,
            "username": db_config_res.username,
        }
        if db_config_res
        else None,
    )


@router.patch("")
async def update_tenant_config(
    body: TenantConfigUpdate,
    current_user: Any = Depends(get_current_user),
) -> TenantConfigResponse:
    """Update tenant limits.

    Only admin can update tenant configuration.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    if (
        body.daily_token_limit is None
        and body.max_row_limit is None
        and body.max_export_row_limit is None
        and body.export_batch_size is None
        and body.export_link_ttl_days is None
        and body.db_config is None
        and body.language is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        async with get_sessionmaker()() as session:
            # Handle Quotas (scoped to this customer)
            if body.daily_token_limit is not None:
                q_customer = (
                    await session.execute(select(Customer).where(Customer.slug == workspace_id))
                ).scalar_one_or_none()
                if not q_customer:
                    raise HTTPException(status_code=404, detail="Customer workspace not found")
                quota = (
                    await session.execute(
                        select(TokenQuota)
                        .where(
                            TokenQuota.is_active.is_(True), TokenQuota.customer_id == q_customer.id
                        )
                        .order_by(TokenQuota.created_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if quota:
                    quota.token_limit = body.daily_token_limit
                    log.info(
                        "admin.tenant: Updated quota %s: token_limit=%d",
                        quota.id,
                        quota.token_limit,
                    )
                else:
                    new_quota = TokenQuota(
                        customer_id=q_customer.id,
                        token_limit=body.daily_token_limit,
                        is_active=True,
                    )
                    session.add(new_quota)
                    quota = new_quota
                    log.info(
                        "admin.tenant: Created customer quota: token_limit=%d", quota.token_limit
                    )

            # Handle language (stored on Customer.settings JSONB)
            if body.language is not None:
                customer_l = (
                    await session.execute(select(Customer).where(Customer.slug == workspace_id))
                ).scalar_one_or_none()
                if not customer_l:
                    raise HTTPException(status_code=404, detail="Customer workspace not found")
                customer_l.settings = {**(customer_l.settings or {}), "language": body.language}
                log.info("admin.tenant: set language=%s for %s", body.language, workspace_id)

            # Handle DB Config
            db_config_res = None
            if body.db_config is not None:
                customer = (
                    await session.execute(select(Customer).where(Customer.slug == workspace_id))
                ).scalar_one_or_none()
                if not customer:
                    raise HTTPException(status_code=404, detail="Customer workspace not found")

                db_config_res = (
                    await session.execute(
                        select(CustomerDBConfig).where(CustomerDBConfig.customer_id == customer.id)
                    )
                ).scalar_one_or_none()

                if db_config_res:
                    db_config_res.db_type = body.db_config.db_type
                    db_config_res.host = body.db_config.host
                    db_config_res.port = body.db_config.port
                    db_config_res.database = body.db_config.database
                    db_config_res.username = body.db_config.username
                    if body.max_row_limit is not None:
                        db_config_res.max_row_limit = body.max_row_limit
                    if body.max_export_row_limit is not None:
                        db_config_res.max_export_row_limit = body.max_export_row_limit
                    if body.export_batch_size is not None:
                        db_config_res.export_batch_size = body.export_batch_size
                    if body.export_link_ttl_days is not None:
                        db_config_res.export_link_ttl_days = body.export_link_ttl_days
                    if body.db_config.password:
                        db_config_res.encrypted_password = await async_encrypt_password(
                            body.db_config.password, customer.id, session
                        )
                else:
                    db_config_res = CustomerDBConfig(
                        customer_id=customer.id,
                        name=f"{workspace_id} DB",
                        db_type=body.db_config.db_type,
                        host=body.db_config.host,
                        port=body.db_config.port,
                        database=body.db_config.database,
                        username=body.db_config.username,
                        max_row_limit=body.max_row_limit or DEFAULT_MAX_ROW_LIMIT,
                        max_export_row_limit=body.max_export_row_limit
                        or DEFAULT_MAX_EXPORT_ROW_LIMIT,
                        export_batch_size=body.export_batch_size
                        or DEFAULT_EXPORT_BATCH_SIZE,
                        export_link_ttl_days=body.export_link_ttl_days
                        or DEFAULT_EXPORT_LINK_TTL_DAYS,
                        encrypted_password=await async_encrypt_password(
                            body.db_config.password, customer.id, session
                        )
                        if body.db_config.password
                        else await async_encrypt_password("", customer.id, session),
                    )
                    session.add(db_config_res)

            elif (
                body.max_row_limit is not None
                or body.max_export_row_limit is not None
                or body.export_batch_size is not None
                or body.export_link_ttl_days is not None
            ):
                # NOTE: if no CustomerDBConfig row exists for this workspace these
                # limit fields are silently dropped (and the invariant is skipped).
                # Every workspace is backfilled in practice; if that ever changes,
                # this branch would need a CREATE path like the db_config branch.
                # If only row/export limit fields are updated but db_config is empty
                customer = (
                    await session.execute(select(Customer).where(Customer.slug == workspace_id))
                ).scalar_one_or_none()
                if customer:
                    db_config_res = (
                        await session.execute(
                            select(CustomerDBConfig).where(
                                CustomerDBConfig.customer_id == customer.id
                            )
                        )
                    ).scalar_one_or_none()
                    if db_config_res:
                        if body.max_row_limit is not None:
                            db_config_res.max_row_limit = body.max_row_limit
                        if body.max_export_row_limit is not None:
                            db_config_res.max_export_row_limit = body.max_export_row_limit
                        if body.export_batch_size is not None:
                            db_config_res.export_batch_size = body.export_batch_size
                        if body.export_link_ttl_days is not None:
                            db_config_res.export_link_ttl_days = body.export_link_ttl_days

            if db_config_res is not None:
                try:
                    validate_row_limit_invariant(
                        max_row=db_config_res.max_row_limit,
                        max_export=db_config_res.max_export_row_limit,
                        batch=db_config_res.export_batch_size,
                    )
                except ValueError as e:
                    await session.rollback()
                    raise HTTPException(status_code=400, detail=str(e)) from e

            await session.commit()

        # For response
        final_limit = (
            body.daily_token_limit
            if body.daily_token_limit is not None
            else DEFAULT_DAILY_TOKEN_LIMIT
        )
        return TenantConfigResponse(
            daily_token_limit=final_limit,
            max_row_limit=db_config_res.max_row_limit if db_config_res else DEFAULT_MAX_ROW_LIMIT,
            max_export_row_limit=(
                db_config_res.max_export_row_limit if db_config_res else DEFAULT_MAX_EXPORT_ROW_LIMIT
            ),
            export_batch_size=(
                db_config_res.export_batch_size if db_config_res else DEFAULT_EXPORT_BATCH_SIZE
            ),
            export_link_ttl_days=(
                db_config_res.export_link_ttl_days
                if db_config_res
                else DEFAULT_EXPORT_LINK_TTL_DAYS
            ),
            source="db",
            language=await get_workspace_language(workspace_id),
            db_config={
                "db_type": body.db_config.db_type.value
                if hasattr(body.db_config.db_type, "value")
                else str(body.db_config.db_type),
                "host": body.db_config.host,
                "port": body.db_config.port,
                "database": body.db_config.database,
                "username": body.db_config.username,
            }
            if body.db_config
            else None,
        )

    except SQLAlchemyError as exc:
        log.error("admin.tenant: Failed to update config: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant config. Check server logs.",
        ) from exc
