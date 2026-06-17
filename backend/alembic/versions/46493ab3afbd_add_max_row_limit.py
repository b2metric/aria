"""add_max_row_limit

Revision ID: 46493ab3afbd
Revises: 13d762fcf236
Create Date: 2026-06-15 22:05:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '46493ab3afbd'
down_revision: Union[str, None] = '4ca2dfad6087'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('customer_db_configs', sa.Column('max_row_limit', sa.Integer(), server_default='1000', nullable=False, comment='Hard limit for rows returned per query'))

def downgrade() -> None:
    op.drop_column('customer_db_configs', 'max_row_limit')
