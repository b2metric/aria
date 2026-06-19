"""initial_schema — all 13 tables + 10 enum types.

Embeddings are plain Postgres float arrays; vector search lives in Qdrant
(LOCKED-DECISIONS #1: pgvector REMOVED). No vector extension is required.

Revision ID: ce0a16365076
Revises:
Create Date: 2026-06-07 02:08:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "ce0a16365076"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── Enum names (used in both upgrade and downgrade) ─────────────────────
ENUMS = [
    ("user_role", ["admin", "member", "viewer"]),
    ("team_role", ["owner", "admin", "member"]),
    ("query_status", ["pending", "running", "completed", "failed", "cancelled"]),
    ("artifact_type", ["chart", "dashboard", "report", "insight"]),
    ("artifact_status", ["draft", "published", "archived"]),
    ("job_status", ["pending", "running", "completed", "failed", "cancelled"]),
    ("job_type", ["schema_sync", "insight_gen", "report_gen", "data_export"]),
    (
        "database_type",
        ["postgresql", "mysql", "bigquery", "snowflake", "redshift", "mssql", "oracle"],
    ),
    ("knowledge_type", ["sql_pattern", "business_term", "metric_def", "relationship_def"]),
    ("quota_period", ["daily", "monthly"]),
]


def upgrade() -> None:
    # ── Enum types ───────────────────────────────────────────────────
    for name, values in ENUMS:
        enum_type = postgresql.ENUM(*values, name=name, create_type=False)
        enum_type.create(op.get_bind(), checkfirst=True)

    # ── customers ────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("plan", sa.String(50), server_default="free"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── teams ────────────────────────────────────────────────────────
    op.create_table(
        "teams",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
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
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "member", "viewer", name="user_role", create_type=False),
            server_default="member",
        ),
        sa.Column(
            "external_id", sa.String(255), unique=True, nullable=True, comment="Keycloak user ID"
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── customer_db_configs ──────────────────────────────────────────
    op.create_table(
        "customer_db_configs",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "db_type",
            postgresql.ENUM(
                "postgresql",
                "mysql",
                "bigquery",
                "snowflake",
                "redshift",
                "mssql",
                "oracle",
                name="database_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("host", sa.String(512), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False, comment="Encrypted at rest"),
        sa.Column("ssl_mode", sa.String(50), server_default="prefer"),
        sa.Column(
            "extra_params",
            postgresql.JSONB(),
            nullable=True,
            comment="Extra connection params as JSON",
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── queries ──────────────────────────────────────────────────────
    op.create_table(
        "queries",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("natural_language", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="query_status",
                create_type=False,
            ),
            server_default="pending",
        ),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("rows_returned", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "db_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customer_db_configs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── query_history ────────────────────────────────────────────────
    op.create_table(
        "query_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "query_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sql_executed", sa.Text(), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column("rows_returned", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── artifacts ────────────────────────────────────────────────────
    op.create_table(
        "artifacts",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "query_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "type",
            postgresql.ENUM(
                "chart", "dashboard", "report", "insight", name="artifact_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "published", "archived", name="artifact_status", create_type=False
            ),
            server_default="draft",
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("s3_key", sa.String(1024), nullable=True, comment="MinIO object key"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── background_jobs ──────────────────────────────────────────────
    op.create_table(
        "background_jobs",
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
                "schema_sync",
                "insight_gen",
                "report_gen",
                "data_export",
                name="job_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="job_status",
                create_type=False,
            ),
            server_default="pending",
        ),
        sa.Column("params", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prefect_flow_run_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

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
                "sql_pattern",
                "business_term",
                "metric_def",
                "relationship_def",
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

    # ── schema_relationships ─────────────────────────────────────────
    op.create_table(
        "schema_relationships",
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
            "db_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customer_db_configs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_table", sa.String(512), nullable=False),
        sa.Column("source_column", sa.String(512), nullable=False),
        sa.Column("target_table", sa.String(512), nullable=False),
        sa.Column("target_column", sa.String(512), nullable=False),
        sa.Column(
            "relationship_type",
            sa.String(50),
            server_default="inferred",
            comment="one_to_one, one_to_many, many_to_many, inferred",
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            server_default=sa.text("0.0"),
            comment="0.0 – 1.0 confidence score",
        ),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── token_quotas ─────────────────────────────────────────────────
    op.create_table(
        "token_quotas",
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
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "period",
            postgresql.ENUM("daily", "monthly", name="quota_period", create_type=False),
            server_default="daily",
        ),
        sa.Column("token_limit", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── token_usage_daily ────────────────────────────────────────────
    op.create_table(
        "token_usage_daily",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("usage_date", sa.Date(), nullable=False, index=True),
        sa.Column("tokens_used", sa.BigInteger(), server_default=sa.text("0")),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Composite indexes ────────────────────────────────────────────
    op.create_index(
        "ix_token_usage_daily_user_date",
        "token_usage_daily",
        ["user_id", "usage_date"],
        unique=False,
    )
    op.create_index(
        "ix_memory_entries_customer_key", "memory_entries", ["customer_id", "key"], unique=False
    )
    op.create_index(
        "ix_vault_knowhow_customer_type", "vault_knowhow", ["customer_id", "type"], unique=False
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("token_usage_daily")
    op.drop_table("token_quotas")
    op.drop_table("schema_relationships")
    op.drop_table("vault_knowhow")
    op.drop_table("memory_entries")
    op.drop_table("background_jobs")
    op.drop_table("artifacts")
    op.drop_table("query_history")
    op.drop_table("queries")
    op.drop_table("customer_db_configs")
    op.drop_table("users")
    op.drop_table("teams")
    op.drop_table("customers")

    # Drop enum types
    for name, _ in reversed(ENUMS):
        op.execute(sa.text(f"DROP TYPE IF EXISTS {name}"))
