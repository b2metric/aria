import uuid
import logging
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import get_settings
from backend.app.models.database import CustomerLLMConfig
from backend.app.models.organization import Customer
from backend.app.services.crypto import async_decrypt_password

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ResolvedLLM:
    """Resolved LLM configuration for a specific customer or platform default."""
    api_base: str
    api_key: str
    model: str
    custom_llm_provider: str
    source: str  # "customer_byok" or "platform_default"
    
    def __repr__(self) -> str:
        """Mask API key in representation."""
        masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 8 else "****"
        return f"<ResolvedLLM source={self.source} provider={self.custom_llm_provider} model={self.model} api_base={self.api_base} api_key={masked_key}>"

async def resolve_llm(workspace_id: str, session: AsyncSession) -> ResolvedLLM:
    """Resolve the LLM configuration for a given workspace.
    
    If the customer has BYOK configured and enabled, return their dedicated proxy credentials.
    Otherwise, fall back to the platform default (from settings).
    """
    settings = get_settings()
    
    # 1. Platform default fallback
    default_llm = ResolvedLLM(
        api_base=settings.litellm_api_base,
        api_key=settings.litellm_api_key or "",
        model=settings.llm_model,
        custom_llm_provider="litellm",
        source="platform_default"
    )
    
    if not workspace_id or workspace_id == "default":
        return default_llm
        
    try:
        # Lookup customer by slug
        customer = (await session.execute(select(Customer).where(Customer.slug == workspace_id))).scalar_one_or_none()
        
        if customer:
            # Check for active LLM config
            llm_config = (
                await session.execute(
                    select(CustomerLLMConfig)
                    .where(CustomerLLMConfig.customer_id == customer.id)
                    .where(CustomerLLMConfig.enabled.is_(True))
                    .where(CustomerLLMConfig.is_active.is_(True))
                )
            ).scalar_one_or_none()
            
            if llm_config:
                # Decrypt their virtual key (using the global decrypt_password for Phase 1)
                # In Phase 2, this will use decrypt_for_customer
                virtual_key = await async_decrypt_password(llm_config.encrypted_virtual_key, llm_config.customer_id, session) if llm_config.encrypted_virtual_key else ""
                
                return ResolvedLLM(
                    api_base=settings.litellm_api_base, # We route everything through our LiteLLM proxy
                    api_key=virtual_key,
                    model=llm_config.model_name,
                    custom_llm_provider="litellm",
                    source="customer_byok"
                )
                
    except Exception as exc:
        logger.warning(f"Failed to resolve LLM config for workspace {workspace_id}: {exc}. Falling back to default.")
        
    return default_llm
