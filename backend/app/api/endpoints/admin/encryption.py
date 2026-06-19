import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.database import CustomerKeyConfig
from backend.app.models.organization import Customer

log = logging.getLogger("aria.admin.encryption")
router = APIRouter()

class EncryptionConfigResponse(BaseModel):
    provider: str
    key_uri: str | None = None
    is_active: bool

class EncryptionConfigUpdate(BaseModel):
    provider: str = Field(..., description="Provider type: app, aws, gcp, azure")
    key_uri: str | None = Field(default=None, description="URI of the external Key-Encryption-Key")

@router.get("", response_model=EncryptionConfigResponse)
async def get_encryption_config(
    current_user: Any = Depends(get_current_user),
):
    """Get the CMEK/Encryption configuration for the tenant."""
    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        async with get_sessionmaker()() as session:
            customer = (await session.execute(select(Customer).where(Customer.slug == workspace_id))).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found")

            config = (await session.execute(
                select(CustomerKeyConfig).where(CustomerKeyConfig.customer_id == customer.id)
            )).scalar_one_or_none()

            if not config:
                return EncryptionConfigResponse(provider="app", key_uri=None, is_active=True)

            return EncryptionConfigResponse(
                provider=config.provider,
                key_uri=config.key_uri,
                is_active=config.is_active
            )
    except SQLAlchemyError as exc:
        log.error("Failed to fetch encryption config: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")

@router.patch("", response_model=EncryptionConfigResponse)
async def update_encryption_config(
    body: EncryptionConfigUpdate,
    current_user: Any = Depends(get_current_user),
):
    """Update CMEK/Encryption configuration.
    
    If switching providers (e.g. app -> aws), in a full implementation this would 
    re-wrap the DEK using the new KEK. For MVP, we save the configuration.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=403, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    if body.provider not in ["app", "aws", "gcp", "azure"]:
        raise HTTPException(status_code=400, detail="Invalid provider. Must be one of: app, aws, gcp, azure")

    try:
        async with get_sessionmaker()() as session:
            customer = (await session.execute(select(Customer).where(Customer.slug == workspace_id))).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found")

            config = (await session.execute(
                select(CustomerKeyConfig).where(CustomerKeyConfig.customer_id == customer.id)
            )).scalar_one_or_none()

            if config:
                # If provider changed, we log it (actual DEK re-wrapping would require AWS/GCP SDKs)
                if config.provider != body.provider:
                    log.info(f"Tenant {workspace_id} switching KEK provider from {config.provider} to {body.provider}")
                
                config.provider = body.provider
                config.key_uri = body.key_uri
            else:
                raise HTTPException(status_code=400, detail="Encryption config not initialized. Run backfill script.")

            await session.commit()
            
            return EncryptionConfigResponse(
                provider=config.provider,
                key_uri=config.key_uri,
                is_active=config.is_active
            )
    except SQLAlchemyError as exc:
        log.error("Failed to update encryption config: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")
