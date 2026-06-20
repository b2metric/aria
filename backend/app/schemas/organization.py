"""Pydantic schemas for teams and users (admin CRUD endpoints)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import UserRole

# ── Teams ────────────────────────────────────────────────────────────


class TeamBase(BaseModel):
    """Fields shared across team schemas."""

    name: str = Field(..., min_length=1, max_length=255, description="Team name")


class TeamCreate(TeamBase):
    """Payload for creating a new team."""

    pass


class TeamResponse(TeamBase):
    """Public representation of a team."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Users ────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Payload for creating a new user (invitation/manual creation)."""

    email: str = Field(..., description="User's email address")
    display_name: str = Field(..., description="User's full name")
    role: UserRole = Field(default=UserRole.VIEWER, description="User's role")
    team_id: uuid.UUID | None = Field(
        default=None, description="Assign to a team (None to remove from team)"
    )


class UserUpdate(BaseModel):
    """Payload for updating a user's role and/or team assignment."""

    role: UserRole | None = Field(default=None, description="New role for the user")
    team_id: uuid.UUID | None = Field(
        default=None, description="Assign to a team (None to remove from team)"
    )
    sql_visibility: bool | None = Field(
        default=None,
        description=(
            "Per-user SQL-visibility override. NULL inherits the role default; "
            "True/False explicitly overrides who may see raw SQL + raw rows. "
            "Only applied when explicitly present in the request body."
        ),
    )


class UserResponse(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    team_id: uuid.UUID | None
    customer_id: uuid.UUID
    is_active: bool
    sql_visibility: bool | None = None
    created_at: datetime
    updated_at: datetime
