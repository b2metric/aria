"""update_user_roles_enum

Revision ID: 88b86ace576f
Revises: a25091216115
Create Date: 2026-06-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88b86ace576f'
down_revision: Union[str, None] = 'a25091216115'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adding new enum values manually in PostgreSQL (requires COMMIT to finish ongoing transactions before ALTER TYPE)
    op.execute("COMMIT")
    try:
        op.execute("ALTER TYPE user_role ADD VALUE 'team_lead'")
    except Exception:
        pass
    try:
        op.execute("ALTER TYPE user_role ADD VALUE 'analyst'")
    except Exception:
        pass


def downgrade() -> None:
    # Downgrading enums in PostgreSQL is tricky, generally we leave the new values
    pass
