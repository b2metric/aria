"""add export_jobs table

Revision ID: 1051dda49254
Revises: 03a3c29156e0
Create Date: 2026-07-01

Durable record for batched-streaming CSV exports dispatched from chat (Phase 3).
One row per export, advanced queued → running → success/error by the Prefect
export flow.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "1051dda49254"
down_revision: str | None = "03a3c29156e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("conversation_id", sa.String(255), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("sql", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_estimate", sa.Integer(), nullable=True),
        sa.Column("minio_key", sa.String(1024), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("prefect_flow_run_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_export_jobs_id", "export_jobs", ["id"])
    op.create_index("ix_export_jobs_workspace_id", "export_jobs", ["workspace_id"])
    op.create_index("ix_export_jobs_conversation_id", "export_jobs", ["conversation_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_export_jobs_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_conversation_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_workspace_id", table_name="export_jobs")
    op.drop_table("export_jobs")
