"""Query processing models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    """Current UTC time as a tz-naive ISO-8601 string.

    Uses timezone-aware ``datetime.now(UTC)`` (``utcnow()`` is deprecated) but
    drops the offset to keep the exact stored-history wire format unchanged.
    """
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


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


class QueryStatus(StrEnum):
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
    # Presigned/public MinIO link to the full-result CSV export (item 25): persisted
    # so the download link survives F5 / history reload, not just the live SSE event.
    csv_url: str | None = None
    chart_spec: dict[str, Any] | None = None
    # Chart DATA points (JSON rows) for client-side recharts rendering.
    # Preferred over chart_html: avoids persisting multi-MB inline Plotly HTML.
    chart_data: list[dict[str, Any]] | None = None
    summary: str | None = None
    suggestions: list[str] | None = None
    # Per-turn debug trace (item 23): model, row_count, sql_generated, memory
    # context that influenced generation. Surfaced in /admin/conversations.
    trace: dict[str, Any] | None = None
    # Async CSV export dispatched for this turn (massive-export): lets the chat
    # reload re-render the export bubble + download button instead of losing the
    # turn (the export path returns before the normal assistant-message save).
    export_job_id: str | None = None
    timestamp: str = Field(default_factory=_utcnow_iso)


class Conversation(BaseModel):
    """A full conversation thread."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    user_id: str
    title: str = "New conversation"
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)


class QueryResponse(BaseModel):
    """Final response returned after SSE stream completes."""

    conversation_id: str
    status: str
    sql: str | None = None
    explanation: str | None = None
    chart_spec: dict[str, Any] | None = None
    error: str | None = None
