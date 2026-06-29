"""add team_id to data_audit_logs

Adds a PLAIN nullable, indexed ``uuid`` ``team_id`` column to
``data_audit_logs`` so dashboard activity can be filtered/grouped by team
("team/user bazlı da filtreleyip görmek isterim").

NO foreign key by design: team identifiers in tokens can be non-UUID group
names (e.g. "platform") with no provisioned ``teams`` row.  An FK would raise
on insert and fail the whole audit write — dropping the row AND its user
attribution.  A plain indexed uuid still supports ``GROUP BY team_id`` and
equality filters while never blocking a write.

Revision ID: b163496fb992
Revises: e8b1f4a2c9d7
Create Date: 2026-06-29 19:11:36.934918
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "b163496fb992"
down_revision: str | None = "e8b1f4a2c9d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_audit_logs", sa.Column("team_id", sa.Uuid(), nullable=True))
    op.create_index("ix_data_audit_logs_team_id", "data_audit_logs", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_data_audit_logs_team_id", table_name="data_audit_logs")
    op.drop_column("data_audit_logs", "team_id")
