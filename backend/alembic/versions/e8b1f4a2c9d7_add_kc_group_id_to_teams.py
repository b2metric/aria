"""add_kc_group_id_to_teams

Adds the nullable ``kc_group_id`` VARCHAR column to ``teams`` (TIER 3 item 30).
Each team is backed by a Keycloak group whose id is stored here so JWT ``groups``
claims (team-scoped SSO/RLS) resolve and so deletes can clean up the right KC
group. NULL means no KC group is linked yet (pre-existing teams, or a create that
happened while Keycloak was unreachable); such teams can be re-synced later.

Revision ID: e8b1f4a2c9d7
Revises: d7f3a1c9e024
Create Date: 2026-06-29 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "e8b1f4a2c9d7"
down_revision: str | None = "d7f3a1c9e024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "teams",
        sa.Column(
            "kc_group_id",
            sa.String(length=255),
            nullable=True,
            comment=(
                "Keycloak group id backing this team. NULL = no KC group linked yet "
                "(pre-existing team or create during a KC outage). Drives team-scoped "
                "JWT `groups` claims (SSO/RLS) and KC-group cleanup on delete."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("teams", "kc_group_id")
