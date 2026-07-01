"""add token_usage_events + cost_usd on token_usage_daily

Granular per-LLM-call metering (operation / model / conversation / USD cost) plus a
daily cost rollup. Source of truth for per-operation & per-conversation breakdowns.

Revision ID: b2c1a4d7e9f0
Revises: 084c6880bb31
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c1a4d7e9f0"
down_revision: str | None = "084c6880bb31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "token_usage_daily",
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
    )

    op.create_table(
        "token_usage_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("team_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", sa.String(255), nullable=True),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_token_usage_events_customer_id", "token_usage_events", ["customer_id"])
    op.create_index("ix_token_usage_events_user_id", "token_usage_events", ["user_id"])
    op.create_index(
        "ix_token_usage_events_conversation_id", "token_usage_events", ["conversation_id"]
    )
    op.create_index("ix_token_usage_events_operation", "token_usage_events", ["operation"])
    op.create_index("ix_token_usage_events_created_at", "token_usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("token_usage_events")
    op.drop_column("token_usage_daily", "cost_usd")
