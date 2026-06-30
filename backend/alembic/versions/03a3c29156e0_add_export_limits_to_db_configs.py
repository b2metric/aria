"""add export-limit columns to customer_db_configs

Revision ID: 03a3c29156e0
Revises: b163496fb992
Create Date: 2026-06-30

Adds max_export_row_limit (export ceiling) and export_batch_size (streaming
batch size). Backfills export ceiling from the existing display limit so no
tenant's export cap is below its current query cap.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "03a3c29156e0"
down_revision: str | None = "b163496fb992"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_db_configs",
        sa.Column(
            "max_export_row_limit",
            sa.Integer(),
            nullable=False,
            server_default="100000",
        ),
    )
    # export_batch_size needs no backfill: every row keeps its server_default
    # of 50000, which is <= the default export ceiling (100000).
    op.add_column(
        "customer_db_configs",
        sa.Column(
            "export_batch_size",
            sa.Integer(),
            nullable=False,
            server_default="50000",
        ),
    )
    # Backfill: export ceiling never below the existing display ceiling.
    op.execute(
        "UPDATE customer_db_configs "
        "SET max_export_row_limit = GREATEST(max_row_limit, 100000)"
    )


def downgrade() -> None:
    op.drop_column("customer_db_configs", "export_batch_size")
    op.drop_column("customer_db_configs", "max_export_row_limit")
