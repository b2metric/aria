"""add_customer_key_config

Revision ID: 4dff463b5ea2
Revises: 88b86ace576f
Create Date: 2026-06-17 17:26:06.295560
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '4dff463b5ea2'
down_revision: Union[str, None] = '88b86ace576f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('customer_key_configs',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('provider', sa.String(length=50), server_default='app', nullable=False, comment='app, aws, gcp, azure'),
    sa.Column('key_uri', sa.String(length=512), nullable=True, comment='URI to the KEK in the provider'),
    sa.Column('encrypted_dek', sa.Text(), nullable=False, comment='Data Encryption Key encrypted by KEK'),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_key_configs_customer_id'), 'customer_key_configs', ['customer_id'], unique=False)
    op.create_index(op.f('ix_customer_key_configs_id'), 'customer_key_configs', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_customer_key_configs_id'), table_name='customer_key_configs')
    op.drop_index(op.f('ix_customer_key_configs_customer_id'), table_name='customer_key_configs')
    op.drop_table('customer_key_configs')

