"""add priced flag to token_usage_events

Sprint 2.5 Task 13/18: split usage into priced (billable / real cost) vs unpriced
(self-hosted / no-price, e.g. a local HF embedder). Set from the cost SOURCE, not
from cost_usd > 0. Backfill existing rows to priced = (cost_usd > 0).

Revision ID: c3d2b5e8f1a4
Revises: b2c1a4d7e9f0
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d2b5e8f1a4"
down_revision: str | None = "b2c1a4d7e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "token_usage_events",
        sa.Column("priced", sa.Boolean(), nullable=False, server_default="true"),
    )
    # Best-effort backfill: pre-existing rows had cost from the local PRICING map, so a
    # positive cost implies priced. Zero-cost historic rows are treated as unpriced.
    op.execute("UPDATE token_usage_events SET priced = (cost_usd > 0)")
    op.create_index(
        "ix_token_usage_events_priced", "token_usage_events", ["priced"]
    )


def downgrade() -> None:
    op.drop_index("ix_token_usage_events_priced", table_name="token_usage_events")
    op.drop_column("token_usage_events", "priced")
