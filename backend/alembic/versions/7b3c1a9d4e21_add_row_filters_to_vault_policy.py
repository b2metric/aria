"""add_row_filters_to_team_vault_policies

Adds the ``row_filters`` JSONB column to ``team_vault_policies`` for row-level
security (RLS).  It holds a per-table predicate map enforced structurally on
generated SQL, e.g. ``{"FCT_SALES": "REGION = 'KW'", "DIM_CUSTOMER": "TENANT_ID = 42"}``.
NULL means no row restriction.

Revision ID: 7b3c1a9d4e21
Revises: 4dff463b5ea2
Create Date: 2026-06-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "7b3c1a9d4e21"
down_revision: str | None = "4dff463b5ea2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "team_vault_policies",
        sa.Column(
            "row_filters",
            postgresql.JSONB(),
            nullable=True,
            comment=(
                "Per-table row-level predicate map enforced structurally on generated SQL, "
                "e.g. {\"FCT_SALES\": \"REGION = 'KW'\", \"DIM_CUSTOMER\": \"TENANT_ID = 42\"}. "
                "NULL/empty means no row restriction."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("team_vault_policies", "row_filters")
