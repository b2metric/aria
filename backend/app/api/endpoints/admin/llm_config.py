import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from backend.app.auth.dependencies import get_current_user
from backend.app.core.config import get_settings
from backend.app.db.session import get_sessionmaker
from backend.app.models.database import CustomerLLMConfig
from backend.app.models.enums import LLMProvider
from backend.app.models.organization import Customer
from backend.app.services.crypto import async_encrypt_password
from backend.app.services.litellm_admin import provision_virtual_key

log = logging.getLogger("aria.admin.llm_config")
router = APIRouter()


class LLMConfigModel(BaseModel):
    provider: LLMProvider
    upstream_api_base: str | None = None
    upstream_api_key: str | None = None
    model_name: str
    deployment_or_version: str | None = None
    enabled: bool = True
    # Per-operation model routing: {operation: {model, temperature?, max_tokens?}}
    # operation ∈ sql_generation/insight/suggestion/chart. Absent → inherit model_name.
    operation_models: dict[str, Any] | None = None


class LLMConfigResponse(BaseModel):
    provider: str
    upstream_api_base: str | None = None
    api_key_set: bool
    model_name: str
    deployment_or_version: str | None = None
    enabled: bool
    operation_models: dict[str, Any] | None = None


@router.get("", response_model=LLMConfigResponse)
async def get_llm_config(current_user: Any = Depends(get_current_user)):
    """Get customer LLM config."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if customer:
                llm_config = (
                    await session.execute(
                        select(CustomerLLMConfig).where(
                            CustomerLLMConfig.customer_id == customer.id
                        )
                    )
                ).scalar_one_or_none()

                if llm_config:
                    return LLMConfigResponse(
                        provider=llm_config.provider.value,
                        upstream_api_base=llm_config.upstream_api_base,
                        api_key_set=bool(llm_config.encrypted_upstream_api_key),
                        model_name=llm_config.model_name,
                        deployment_or_version=llm_config.deployment_or_version,
                        enabled=llm_config.enabled,
                        operation_models=llm_config.operation_models,
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
        enabled=False,
        operation_models=None,
    )


@router.patch("", response_model=LLMConfigResponse)
async def update_llm_config(body: LLMConfigModel, current_user: Any = Depends(get_current_user)):
    """Update customer LLM config."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        async with get_sessionmaker()() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()
            if not customer:
                raise HTTPException(status_code=404, detail="Customer not found")

            llm_config = (
                await session.execute(
                    select(CustomerLLMConfig).where(CustomerLLMConfig.customer_id == customer.id)
                )
            ).scalar_one_or_none()

            if llm_config:
                llm_config.provider = body.provider
                if body.upstream_api_base is not None:
                    llm_config.upstream_api_base = body.upstream_api_base
                if body.upstream_api_key:
                    llm_config.encrypted_upstream_api_key = await async_encrypt_password(
                        body.upstream_api_key, customer.id, session
                    )
                    # Phase 2 (item 27): mint a per-customer LiteLLM virtual key when
                    # a master key is configured; otherwise fall back to passthrough.
                    _settings = get_settings()
                    proxy_key = await provision_virtual_key(
                        api_base=_settings.litellm_api_base,
                        master_key=_settings.litellm_master_key,
                        customer_slug=customer.slug,
                        upstream_key=body.upstream_api_key,
                        model=body.model_name,
                    )
                    llm_config.encrypted_virtual_key = await async_encrypt_password(
                        proxy_key, customer.id, session
                    )
                llm_config.model_name = body.model_name
                llm_config.deployment_or_version = body.deployment_or_version
                llm_config.enabled = body.enabled
                if body.operation_models is not None:
                    llm_config.operation_models = body.operation_models or None
            else:
                # Phase 2 (item 27): provision the proxy key (mint a per-customer
                # virtual key when a master key is set, else passthrough).
                _settings = get_settings()
                proxy_key = await provision_virtual_key(
                    api_base=_settings.litellm_api_base,
                    master_key=_settings.litellm_master_key,
                    customer_slug=customer.slug,
                    upstream_key=body.upstream_api_key or "",
                    model=body.model_name,
                )
                llm_config = CustomerLLMConfig(
                    customer_id=customer.id,
                    provider=body.provider,
                    upstream_api_base=body.upstream_api_base,
                    encrypted_upstream_api_key=await async_encrypt_password(
                        body.upstream_api_key or "", customer.id, session
                    ),
                    encrypted_virtual_key=await async_encrypt_password(
                        proxy_key, customer.id, session
                    ),
                    model_name=body.model_name,
                    deployment_or_version=body.deployment_or_version,
                    enabled=body.enabled,
                    operation_models=body.operation_models or None,
                )
                session.add(llm_config)

            await session.commit()

            return LLMConfigResponse(
                provider=llm_config.provider.value
                if hasattr(llm_config.provider, "value")
                else llm_config.provider,
                upstream_api_base=llm_config.upstream_api_base,
                api_key_set=bool(llm_config.encrypted_upstream_api_key),
                model_name=llm_config.model_name,
                deployment_or_version=llm_config.deployment_or_version,
                enabled=llm_config.enabled,
                operation_models=llm_config.operation_models,
            )
    except Exception as exc:
        log.error(f"Failed to update LLM config: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
