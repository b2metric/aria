"""update_user_roles_enum

Revision ID: 88b86ace576f
Revises: a25091216115
Create Date: 2026-06-16 20:00:00.000000

"""

import contextlib
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "88b86ace576f"
down_revision: str | None = "a25091216115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Adding new enum values manually in PostgreSQL (requires COMMIT to finish ongoing transactions before ALTER TYPE)
    op.execute("COMMIT")
    with contextlib.suppress(Exception):
        op.execute("ALTER TYPE user_role ADD VALUE 'team_lead'")
    with contextlib.suppress(Exception):
        op.execute("ALTER TYPE user_role ADD VALUE 'analyst'")


def downgrade() -> None:
    # Downgrading enums in PostgreSQL is tricky, generally we leave the new values
    pass
