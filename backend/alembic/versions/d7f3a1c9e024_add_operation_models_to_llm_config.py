"""add_operation_models_to_customer_llm_config

Adds the nullable ``operation_models`` JSONB column to ``customer_llm_configs``
for per-operation model routing (Sprint D). Shape:
``{operation: {model, temperature?, max_tokens?}}`` where operation is one of
sql_generation/insight/suggestion/chart. NULL/absent → inherit ``model_name``.

Revision ID: d7f3a1c9e024
Revises: c4e9d2f1a7b3
Create Date: 2026-06-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "d7f3a1c9e024"
down_revision: str | None = "c4e9d2f1a7b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_llm_configs",
        sa.Column(
            "operation_models",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "Per-operation model routing: {operation: {model, temperature?, "
                "max_tokens?}} where operation is one of "
                "sql_generation/insight/suggestion/chart. Absent -> inherit model_name."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("customer_llm_configs", "operation_models")
