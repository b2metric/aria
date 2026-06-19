"""PostgreSQL enum types for ARIA schema.

All enums are created at the database level via Alembic so they can be
used in CHECK constraints and queried directly.
"""

import enum


class UserRole(enum.StrEnum):
    """Role within a customer tenant."""

    ADMIN = "admin"
    TEAM_LEAD = "team_lead"
    ANALYST = "analyst"
    VIEWER = "viewer"


class TeamRole(enum.StrEnum):
    """Role within a team."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class QueryStatus(enum.StrEnum):
    """Lifecycle states of a natural-language query."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(enum.StrEnum):
    """Types of generated output artifacts."""

    CHART = "chart"
    DASHBOARD = "dashboard"
    REPORT = "report"
    INSIGHT = "insight"


class ArtifactStatus(enum.StrEnum):
    """Publishing states for artifacts."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class JobStatus(enum.StrEnum):
    """Lifecycle states of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(enum.StrEnum):
    """Categories of background work."""

    SCHEMA_SYNC = "schema_sync"
    INSIGHT_GEN = "insight_gen"
    REPORT_GEN = "report_gen"
    DATA_EXPORT = "data_export"


class DatabaseType(enum.StrEnum):
    """Supported external database engines."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    REDSHIFT = "redshift"
    MSSQL = "mssql"


class KnowledgeType(enum.StrEnum):
    """Categories of vault knowledge entries."""

    SQL_PATTERN = "sql_pattern"
    BUSINESS_TERM = "business_term"
    METRIC_DEF = "metric_def"
    RELATIONSHIP_DEF = "relationship_def"


class QuotaPeriod(enum.StrEnum):
    """Token quota reset interval."""

    DAILY = "daily"
    MONTHLY = "monthly"


class LLMProvider(enum.StrEnum):
    """Supported LLM providers for BYOK."""

    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    LITELLM = "litellm"
