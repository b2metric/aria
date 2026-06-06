"""Artifact and background-job models."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import ArtifactStatus, ArtifactType, JobStatus, JobType


class Artifact(Base, UUIDMixin, TimestampMixin):
    """Generated output: chart, dashboard, report, or insight."""

    __tablename__ = "artifacts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queries.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[ArtifactType] = mapped_column(nullable=False)
    status: Mapped[ArtifactStatus] = mapped_column(default=ArtifactStatus.DRAFT, server_default="draft")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=sa.text("'{}'::jsonb"))
    s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="MinIO object key")

    def __repr__(self) -> str:
        return f"<Artifact {self.title} [{self.type.value}]>"


class BackgroundJob(Base, UUIDMixin):
    """Async background job with Prefect integration."""

    __tablename__ = "background_jobs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[JobType] = mapped_column(nullable=False)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.PENDING, server_default="pending")
    params: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=sa.text("'{}'::jsonb"))
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefect_flow_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    def __repr__(self) -> str:
        return f"<BackgroundJob {self.type.value} [{self.status.value}]>"
