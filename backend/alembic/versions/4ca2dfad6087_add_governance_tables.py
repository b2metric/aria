"""add_governance_tables

Revision ID: 4ca2dfad6087
Revises: ce0a16365076
Create Date: 2026-06-13 16:41:48.329438
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '4ca2dfad6087'
down_revision: Union[str, None] = 'ce0a16365076'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── team_vault_policies ───────────────────────────────────────────
    op.create_table(
        'team_vault_policies',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            'customer_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('customers.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'team_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('teams.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
            comment='NULL means customer-wide default policy',
        ),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column(
            'allowed_tables',
            postgresql.ARRAY(sa.String()),
            server_default='{}',
            nullable=False,
            comment='Whitelist of table names the team may query',
        ),
        sa.Column(
            'deny_columns',
            postgresql.JSONB(),
            nullable=True,
            comment='Per-table deny-lists, e.g. {"sales": ["revenue", "margin"]}',
        ),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── data_audit_logs ───────────────────────────────────────────────
    op.create_table(
        'data_audit_logs',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            'customer_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('customers.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'action',
            sa.String(100),
            nullable=False,
            comment='e.g. query, export, view, schema_discovery, vault_read',
        ),
        sa.Column(
            'resource_type',
            sa.String(100),
            nullable=False,
            comment='e.g. table, query, artifact, vault_entry, db_config',
        ),
        sa.Column(
            'resource_id',
            sa.String(255),
            nullable=True,
            comment='Identifier of the accessed resource',
        ),
        sa.Column(
            'details',
            postgresql.JSONB(),
            nullable=True,
            comment='Arbitrary payload: SQL text, filters applied, row-count, etc.',
        ),
        sa.Column(
            'ip_address',
            sa.String(45),
            nullable=True,
            comment='Client IP (IPv4 or IPv6)',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table('data_audit_logs')
    op.drop_table('team_vault_policies')
