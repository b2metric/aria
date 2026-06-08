"""Query processing models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming NL query from the chat UI."""

    question: str = Field(..., min_length=1, max_length=4096)
    conversation_id: str | None = Field(
        default=None,
        description="Continue an existing conversation. Omit to start a new one.",
    )
    db_config_id: str | None = Field(
        default=None,
        description="Database configuration to query. Uses workspace default if omitted.",
    )


class QueryStatus(str, Enum):
    THINKING = "thinking"
    GENERATING_SQL = "generating_sql"
    SQL_READY = "sql_ready"
    EXECUTING = "executing"
    RENDERING_CHART = "rendering_chart"
    COMPLETE = "complete"
    ERROR = "error"


class ConversationMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    sql: str | None = None
    chart_html: str | None = None
    chart_url: str | None = None
    chart_spec: dict[str, Any] | None = None
    # Chart DATA points (JSON rows) for client-side recharts rendering.
    # Preferred over chart_html: avoids persisting multi-MB inline Plotly HTML.
    chart_data: list[dict[str, Any]] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Conversation(BaseModel):
    """A full conversation thread."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    user_id: str
    title: str = "New conversation"
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QueryResponse(BaseModel):
    """Final response returned after SSE stream completes."""

    conversation_id: str
    status: str
    sql: str | None = None
    explanation: str | None = None
    chart_spec: dict[str, Any] | None = None
    error: str | None = None
