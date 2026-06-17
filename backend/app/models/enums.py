"""PostgreSQL enum types for ARIA schema.

All enums are created at the database level via Alembic so they can be
used in CHECK constraints and queried directly.
"""

import enum


class UserRole(str, enum.Enum):
    """Role within a customer tenant."""

    ADMIN = "admin"
    TEAM_LEAD = "team_lead"
    ANALYST = "analyst"
    VIEWER = "viewer"



class TeamRole(str, enum.Enum):
    """Role within a team."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class QueryStatus(str, enum.Enum):
    """Lifecycle states of a natural-language query."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(str, enum.Enum):
    """Types of generated output artifacts."""

    CHART = "chart"
    DASHBOARD = "dashboard"
    REPORT = "report"
    INSIGHT = "insight"


class ArtifactStatus(str, enum.Enum):
    """Publishing states for artifacts."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class JobStatus(str, enum.Enum):
    """Lifecycle states of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    """Categories of background work."""

    SCHEMA_SYNC = "schema_sync"
    INSIGHT_GEN = "insight_gen"
    REPORT_GEN = "report_gen"
    DATA_EXPORT = "data_export"


class DatabaseType(str, enum.Enum):
    """Supported external database engines."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    REDSHIFT = "redshift"
    MSSQL = "mssql"


class KnowledgeType(str, enum.Enum):
    """Categories of vault knowledge entries."""

    SQL_PATTERN = "sql_pattern"
    BUSINESS_TERM = "business_term"
    METRIC_DEF = "metric_def"
    RELATIONSHIP_DEF = "relationship_def"


class QuotaPeriod(str, enum.Enum):
    """Token quota reset interval."""

    DAILY = "daily"
    MONTHLY = "monthly"


class LLMProvider(str, enum.Enum):
    """Supported LLM providers for BYOK."""

    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    LITELLM = "litellm"
