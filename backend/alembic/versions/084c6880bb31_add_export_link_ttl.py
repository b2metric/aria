"""add export_link_ttl_days to customer_db_configs

Revision ID: 084c6880bb31
Revises: 1051dda49254
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "084c6880bb31"
down_revision: str | None = "1051dda49254"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_db_configs",
        sa.Column("export_link_ttl_days", sa.Integer(), nullable=False, server_default="3"),
    )


def downgrade() -> None:
    op.drop_column("customer_db_configs", "export_link_ttl_days")
