"""Durable record of a massive-query CSV export (Phase 3).

One row per export request dispatched from the chat pipeline. The async export
flow (``app/flows/export.py``) advances it queued → running → success/error and
records the streamed row count, truncation flag, MinIO key, and download URL.
Workspace-scoped; honors the same RBAC/SQL-visibility invariants as the query
that produced it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class ExportStatus(StrEnum):
    """Lifecycle states for an export job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ExportJob(Base, UUIDMixin, TimestampMixin):
    """A queued/running/finished massive-query CSV export."""

    __tablename__ = "export_jobs"

    # Scope / provenance (string identifiers, matching the pipeline's runtime ids;
    # NOT FKs — workspace_id is a customer slug, user_id may be a Keycloak sub).
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    # Plain String (not a native PG enum like enums.py) — deliberate: app-layer
    # enforced via ExportStatus, keeps the migration simple as states evolve.
    status: Mapped[ExportStatus] = mapped_column(
        String(16), nullable=False, default=ExportStatus.QUEUED, server_default="queued", index=True
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    total_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Result
    minio_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefect_flow_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps (created_at/updated_at come from TimestampMixin)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ExportJob {self.id} [{self.status}] rows={self.row_count}>"
