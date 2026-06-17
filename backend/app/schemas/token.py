"""Pydantic schemas for token quota management."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import QuotaPeriod


class TokenQuotaBase(BaseModel):
    """Fields shared across token quota schemas."""

    team_id: uuid.UUID | None = Field(default=None, description="Scope to a specific team (NULL for customer-wide or user-specific)")
    user_id: uuid.UUID | None = Field(default=None, description="Scope to a specific user (NULL for customer-wide or team-wide)")
    period: QuotaPeriod = Field(default=QuotaPeriod.DAILY, description="Quota reset period")
    token_limit: int = Field(..., ge=1, description="Number of tokens allowed per period")
    is_active: bool = Field(default=True, description="Whether the quota is active")


class TokenQuotaCreate(TokenQuotaBase):
    """Payload for creating a new token quota."""
    pass


class TokenQuotaUpdate(BaseModel):
    """Payload for updating an existing token quota."""
    token_limit: int | None = Field(default=None, ge=1, description="Number of tokens allowed per period")
    is_active: bool | None = Field(default=None, description="Whether the quota is active")


class TokenQuotaResponse(TokenQuotaBase):
    """Public representation of a token quota."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TokenUsageDailyResponse(BaseModel):
    """Public representation of daily token usage."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    user_id: uuid.UUID
    usage_date: str  # Format: YYYY-MM-DD
    tokens_used: int
    model: str
    created_at: datetime