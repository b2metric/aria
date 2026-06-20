import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.database import CustomerKeyConfig
from backend.app.models.organization import Customer
from backend.app.services import crypto
from backend.app.services.audit import AuditService

log = logging.getLogger("aria.admin.encryption")
router = APIRouter()

VALID_PROVIDERS = ("app", "aws", "gcp", "azure")


class EncryptionConfigResponse(BaseModel):
    provider: str
    key_uri: str | None = None
    is_active: bool


class EncryptionStatusResponse(EncryptionConfigResponse):
    reachable: bool = Field(
        ..., description="Whether the configured KEK passes a wrap/unwrap probe"
    )


class EncryptionConfigUpdate(BaseModel):
    provider: str = Field(..., description="Provider type: app, aws, gcp, azure")
    key_uri: str | None = Field(default=None, description="URI of the external Key-Encryption-Key")


def _actor_uuid(current_user: Any) -> uuid.UUID | None:
    """Best-effort parse of the Keycloak subject into a UUID for the audit row."""
    raw = getattr(current_user, "user_id", None) or getattr(current_user, "sub", None)
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        return None


@router.get("", response_model=EncryptionConfigResponse)
async def get_encryption_config(
    current_user: Any = Depends(get_current_user),
):
    """Get the CMEK/Encryption configuration for the tenant."""
    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found")

            config = (
                await session.execute(
                    select(CustomerKeyConfig).where(CustomerKeyConfig.customer_id == customer.id)
                )
            ).scalar_one_or_none()

            if not config:
                return EncryptionConfigResponse(provider="app", key_uri=None, is_active=True)

            return EncryptionConfigResponse(
                provider=config.provider, key_uri=config.key_uri, is_active=config.is_active
            )
    except SQLAlchemyError as exc:
        log.error("Failed to fetch encryption config: %s", exc)
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.get("/status", response_model=EncryptionStatusResponse)
async def get_encryption_status(
    current_user: Any = Depends(get_current_user),
):
    """Configuration plus a live reachability probe of the configured KEK."""
    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found")

            config = (
                await session.execute(
                    select(CustomerKeyConfig).where(CustomerKeyConfig.customer_id == customer.id)
                )
            ).scalar_one_or_none()

            provider = config.provider if config else "app"
            key_uri = config.key_uri if config else None
            is_active = config.is_active if config else True

            try:
                reachable = crypto.get_kek_provider(provider).validate_key(key_uri)
            except crypto.KmsError:
                reachable = False

            return EncryptionStatusResponse(
                provider=provider, key_uri=key_uri, is_active=is_active, reachable=reachable
            )
    except SQLAlchemyError as exc:
        log.error("Failed to fetch encryption status: %s", exc)
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.patch("", response_model=EncryptionConfigResponse)
async def update_encryption_config(
    body: EncryptionConfigUpdate,
    current_user: Any = Depends(get_current_user),
):
    """Update CMEK configuration: validate the key, re-wrap the DEK, audit the change.

    Switching providers (e.g. app → aws) re-wraps the existing DEK under the new
    KEK so already-encrypted data stays decryptable. The new key is validated
    first (fail-fast) and the change is recorded in the audit log.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=403, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}",
        )
    if body.provider != "app" and not body.key_uri:
        raise HTTPException(
            status_code=400, detail="key_uri is required for external KMS providers"
        )

    # Fail fast if the new key is unreachable / lacks wrap+unwrap permission.
    try:
        if not crypto.get_kek_provider(body.provider).validate_key(body.key_uri):
            raise HTTPException(
                status_code=400,
                detail="Key validation failed: the KMS key is unreachable or lacks wrap/unwrap permission.",
            )
    except crypto.KmsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found")

            config = (
                await session.execute(
                    select(CustomerKeyConfig).where(CustomerKeyConfig.customer_id == customer.id)
                )
            ).scalar_one_or_none()
            if not config:
                raise HTTPException(
                    status_code=400,
                    detail="Encryption config not initialized. Run backfill script.",
                )

            old_provider, old_key_uri = config.provider, config.key_uri
            changed = old_provider != body.provider or old_key_uri != body.key_uri

            if changed:
                # Re-wrap the DEK under the new KEK so existing data still decrypts.
                try:
                    config.encrypted_dek = crypto.rewrap_dek(
                        config.encrypted_dek,
                        old_provider=old_provider,
                        old_key_uri=old_key_uri,
                        new_provider=body.provider,
                        new_key_uri=body.key_uri,
                    )
                except crypto.KmsError as exc:
                    raise HTTPException(
                        status_code=400, detail=f"DEK re-wrap failed: {exc}"
                    ) from exc

            config.provider = body.provider
            config.key_uri = body.key_uri
            await session.commit()
            crypto.evict_dek_cache(customer.id)

            if changed:
                await AuditService(session).log_event(
                    customer_id=customer.id,
                    user_id=_actor_uuid(current_user),
                    action="cmek_config_change",
                    resource_type="encryption",
                    resource_id=str(customer.id),
                    details={
                        "old_provider": old_provider,
                        "new_provider": body.provider,
                        "old_key_uri": old_key_uri,
                        "new_key_uri": body.key_uri,
                        "actor": getattr(current_user, "sub", None),
                        "success": True,
                    },
                )

            return EncryptionConfigResponse(
                provider=config.provider, key_uri=config.key_uri, is_active=config.is_active
            )
    except SQLAlchemyError as exc:
        log.error("Failed to update encryption config: %s", exc)
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.post("/rotate", response_model=EncryptionConfigResponse)
async def rotate_encryption_key(
    current_user: Any = Depends(get_current_user),
):
    """Rotate the KEK: re-wrap the DEK under the current key's latest version.

    For external KMS this picks up the newest key version; for the app KEK it
    re-wraps the DEK. The DEK itself (and therefore stored ciphertext) is
    unchanged, so no data re-encryption is required. The rotation is audited.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=403, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found")

            config = (
                await session.execute(
                    select(CustomerKeyConfig).where(CustomerKeyConfig.customer_id == customer.id)
                )
            ).scalar_one_or_none()
            if not config:
                raise HTTPException(status_code=400, detail="Encryption config not initialized.")

            try:
                config.encrypted_dek = crypto.rewrap_dek(
                    config.encrypted_dek,
                    old_provider=config.provider,
                    old_key_uri=config.key_uri,
                    new_provider=config.provider,
                    new_key_uri=config.key_uri,
                )
            except crypto.KmsError as exc:
                raise HTTPException(status_code=400, detail=f"Key rotation failed: {exc}") from exc

            await session.commit()
            crypto.evict_dek_cache(customer.id)

            await AuditService(session).log_event(
                customer_id=customer.id,
                user_id=_actor_uuid(current_user),
                action="cmek_key_rotation",
                resource_type="encryption",
                resource_id=str(customer.id),
                details={
                    "provider": config.provider,
                    "key_uri": config.key_uri,
                    "actor": getattr(current_user, "sub", None),
                    "success": True,
                },
            )

            return EncryptionConfigResponse(
                provider=config.provider, key_uri=config.key_uri, is_active=config.is_active
            )
    except SQLAlchemyError as exc:
        log.error("Failed to rotate encryption key: %s", exc)
        raise HTTPException(status_code=500, detail="Database error") from exc
