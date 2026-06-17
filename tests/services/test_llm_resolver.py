import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.services.llm_resolver import resolve_llm, ResolvedLLM

@pytest.mark.asyncio
async def test_resolve_llm_default():
    # If workspace is "default" or None, should return platform default
    session = AsyncMock()
    resolved = await resolve_llm("default", session)
    
    assert resolved.source == "platform_default"
    assert resolved.custom_llm_provider == "litellm"
    assert "sk-" in resolved.api_key or resolved.api_key == ""
    assert "****" in repr(resolved) or "sk-" in repr(resolved)

@pytest.mark.asyncio
async def test_resolve_llm_no_customer_found():
    # If customer is not found, fallback to default
    session = AsyncMock()
    # Mock scalar_one_or_none to return None
    session.execute.return_value.scalar_one_or_none.return_value = None
    
    resolved = await resolve_llm("non-existent-ws", session)
    assert resolved.source == "platform_default"
