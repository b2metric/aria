"""drop_unused_memory_entries_and_vault_knowhow_tables

Removes two orphan tables created in the initial schema (``ce0a16365076``) that
were never read or written by the application. The real memory system lives in
``backend/app/memory/service.py`` backed by Qdrant (LOCKED-DECISIONS #1), and the
``MemoryEntry`` / ``VaultKnowhow`` SQLAlchemy models had no callers anywhere.

This drops:
  * ``memory_entries`` (+ its indexes)
  * ``vault_knowhow`` (+ its indexes)
  * the ``knowledge_type`` Postgres enum (used only by ``vault_knowhow.type``)

``downgrade()`` faithfully recreates both tables exactly as ``ce0a16365076``
created them (UUID PK, FKs to customers/users, the legacy 1536-d ``embedding``
float array kept in the DB, timestamps, and the ``knowledge_type`` enum).

Revision ID: c4e9d2f1a7b3
Revises: 9a4f2c7e1b88
Create Date: 2026-06-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "c4e9d2f1a7b3"
down_revision: str | None = "9a4f2c7e1b88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Enum used only by vault_knowhow.type — recreated on downgrade.
KNOWLEDGE_TYPE_VALUES = ["sql_pattern", "business_term", "metric_def", "relationship_def"]


def upgrade() -> None:
    # Drop composite indexes first, then the tables (children before the enum).
    op.drop_index("ix_vault_knowhow_customer_type", table_name="vault_knowhow")
    op.drop_index("ix_memory_entries_customer_key", table_name="memory_entries")

    op.drop_table("vault_knowhow")
    op.drop_table("memory_entries")

    # vault_knowhow.type was the only consumer of the knowledge_type enum.
    sa.Enum(name="knowledge_type").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Recreate the knowledge_type enum before the table that uses it.
    knowledge_type = postgresql.ENUM(
        *KNOWLEDGE_TYPE_VALUES, name="knowledge_type", create_type=False
    )
    knowledge_type.create(op.get_bind(), checkfirst=True)

    # ── memory_entries ───────────────────────────────────────────────
    op.create_table(
        "memory_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("key", sa.String(512), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "embedding",
            postgresql.ARRAY(sa.Float(), dimensions=1536),
            nullable=True,
            comment="embedding (1536-d float array; vectors in Qdrant)",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── vault_knowhow ────────────────────────────────────────────────
    op.create_table(
        "vault_knowhow",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "type",
            postgresql.ENUM(
                *KNOWLEDGE_TYPE_VALUES,
                name="knowledge_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'::text[]")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "embedding",
            postgresql.ARRAY(sa.Float(), dimensions=1536),
            nullable=True,
            comment="embedding (1536-d float array; vectors in Qdrant)",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Composite indexes (mirror ce0a16365076) ──────────────────────
    op.create_index(
        "ix_memory_entries_customer_key", "memory_entries", ["customer_id", "key"], unique=False
    )
    op.create_index(
        "ix_vault_knowhow_customer_type", "vault_knowhow", ["customer_id", "type"], unique=False
    )
