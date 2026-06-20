"""add_sql_visibility_override_to_users

Adds the nullable ``sql_visibility`` BOOLEAN column to ``users`` for the
per-user SQL-visibility override (Sprint 16 Task 3).  NULL means the user
inherits the role default (``_can_view_sql`` → admin/analyst); True/False
explicitly overrides who may see the raw SQL string + raw tabular result.

Revision ID: 9a4f2c7e1b88
Revises: 7b3c1a9d4e21
Create Date: 2026-06-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "9a4f2c7e1b88"
down_revision: str | None = "7b3c1a9d4e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "sql_visibility",
            sa.Boolean(),
            nullable=True,
            comment=(
                "Per-user SQL-visibility override. NULL = inherit the role default "
                "(_can_view_sql); True/False explicitly overrides who may see the raw "
                "SQL string + raw tabular result."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "sql_visibility")
