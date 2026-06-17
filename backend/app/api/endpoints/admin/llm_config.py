import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.database import CustomerLLMConfig
from backend.app.models.enums import LLMProvider
from backend.app.models.organization import Customer
from backend.app.services.crypto import encrypt_password

log = logging.getLogger("aria.admin.llm_config")
router = APIRouter()

class LLMConfigModel(BaseModel):
    provider: LLMProvider
    upstream_api_base: str | None = None
    upstream_api_key: str | None = None
    model_name: str
    deployment_or_version: str | None = None
    enabled: bool = True

class LLMConfigResponse(BaseModel):
    provider: str
    upstream_api_base: str | None = None
    api_key_set: bool
    model_name: str
    deployment_or_version: str | None = None
    enabled: bool

@router.get("", response_model=LLMConfigResponse)
async def get_llm_config(current_user: Any = Depends(get_current_user)):
    """Get customer LLM config."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        async with get_sessionmaker()() as session:
            customer = (await session.execute(select(Customer).where(Customer.slug == workspace_id))).scalar_one_or_none()
            if customer:
                llm_config = (await session.execute(
                    select(CustomerLLMConfig).where(CustomerLLMConfig.customer_id == customer.id)
                )).scalar_one_or_none()
                
                if llm_config:
                    return LLMConfigResponse(
                        provider=llm_config.provider.value,
                        upstream_api_base=llm_config.upstream_api_base,
                        api_key_set=bool(llm_config.encrypted_upstream_api_key),
                        model_name=llm_config.model_name,
                        deployment_or_version=llm_config.deployment_or_version,
                        enabled=llm_config.enabled
                    )
    except Exception as exc:
        log.warning(f"Failed to fetch LLM config: {exc}")

    # Return empty representation
    return LLMConfigResponse(
        provider="openai",
        upstream_api_base=None,
        api_key_set=False,
        model_name="gpt-4",
        deployment_or_version=None,
        enabled=False
    )

@router.patch("", response_model=LLMConfigResponse)
async def update_llm_config(body: LLMConfigModel, current_user: Any = Depends(get_current_user)):
    """Update customer LLM config."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        async with get_sessionmaker()() as session:
            customer = (await session.execute(select(Customer).where(Customer.slug == workspace_id))).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Customer not found")

            llm_config = (await session.execute(
                select(CustomerLLMConfig).where(CustomerLLMConfig.customer_id == customer.id)
            )).scalar_one_or_none()
            
            if llm_config:
                llm_config.provider = body.provider
                if body.upstream_api_base is not None:
                    llm_config.upstream_api_base = body.upstream_api_base
                if body.upstream_api_key:
                    llm_config.encrypted_upstream_api_key = encrypt_password(body.upstream_api_key)
                    # For phase 1, virtual key is just the upstream key passed through
                    llm_config.encrypted_virtual_key = encrypt_password(body.upstream_api_key)
                llm_config.model_name = body.model_name
                llm_config.deployment_or_version = body.deployment_or_version
                llm_config.enabled = body.enabled
            else:
                llm_config = CustomerLLMConfig(
                    customer_id=customer.id,
                    provider=body.provider,
                    upstream_api_base=body.upstream_api_base,
                    encrypted_upstream_api_key=encrypt_password(body.upstream_api_key or ""),
                    encrypted_virtual_key=encrypt_password(body.upstream_api_key or ""),
                    model_name=body.model_name,
                    deployment_or_version=body.deployment_or_version,
                    enabled=body.enabled
                )
                session.add(llm_config)
            
            await session.commit()
            
            return LLMConfigResponse(
                provider=llm_config.provider.value if hasattr(llm_config.provider, 'value') else llm_config.provider,
                upstream_api_base=llm_config.upstream_api_base,
                api_key_set=bool(llm_config.encrypted_upstream_api_key),
                model_name=llm_config.model_name,
                deployment_or_version=llm_config.deployment_or_version,
                enabled=llm_config.enabled
            )
    except Exception as exc:
        log.error(f"Failed to update LLM config: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
