"""add_customer_llm_config

Revision ID: a25091216115
Revises: 46493ab3afbd
Create Date: 2026-06-16 19:29:46.989074
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = 'a25091216115'
down_revision: Union[str, None] = '46493ab3afbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the Enum first
    from sqlalchemy.dialects import postgresql
    llm_provider = postgresql.ENUM('openai', 'azure', 'anthropic', 'gemini', 'litellm', name='llm_provider')
    llm_provider.create(op.get_bind())

    op.create_table('customer_llm_configs',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('provider', postgresql.ENUM('openai', 'azure', 'anthropic', 'gemini', 'litellm', name='llm_provider', create_type=False), nullable=False),
    sa.Column('upstream_api_base', sa.String(length=512), nullable=True),
    sa.Column('encrypted_upstream_api_key', sa.Text(), nullable=False, comment='Encrypted at rest'),
    sa.Column('model_name', sa.String(length=255), nullable=False),
    sa.Column('deployment_or_version', sa.String(length=255), nullable=True, comment='Azure deployment name or API version'),
    sa.Column('encrypted_virtual_key', sa.Text(), nullable=True, comment='LiteLLM proxy key (encrypted)'),
    sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('extra_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Extra provider params as JSON'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_llm_configs_customer_id'), 'customer_llm_configs', ['customer_id'], unique=False)
    op.create_index(op.f('ix_customer_llm_configs_id'), 'customer_llm_configs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_customer_llm_configs_id'), table_name='customer_llm_configs')
    op.drop_index(op.f('ix_customer_llm_configs_customer_id'), table_name='customer_llm_configs')
    op.drop_table('customer_llm_configs')
    
    # Drop Enum
    op.execute("DROP TYPE llm_provider")
