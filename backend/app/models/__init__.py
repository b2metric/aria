"""ARIA SQLAlchemy models — import all models so Alembic can discover them."""

from backend.app.models.base import Base
from backend.app.models.organization import Customer, Team, User
from backend.app.models.database import CustomerDBConfig, SchemaRelationship
from backend.app.models.query import Query, QueryHistory
from backend.app.models.artifact import Artifact, BackgroundJob
from backend.app.models.memory import MemoryEntry, VaultKnowhow
from backend.app.models.token import TokenQuota, TokenUsageDaily

__all__ = [
    "Base",
    # Organization
    "Customer",
    "Team",
    "User",
    # Database
    "CustomerDBConfig",
    "SchemaRelationship",
    # Query
    "Query",
    "QueryHistory",
    # Artifacts & Jobs
    "Artifact",
    "BackgroundJob",
    # Memory & Knowledge
    "MemoryEntry",
    "VaultKnowhow",
    # Token
    "TokenQuota",
    "TokenUsageDaily",
]
