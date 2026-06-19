"""Database module — multi-database connection and query execution."""

from backend.app.db.executor import DatabaseExecutor, execute_query, explain_query
from backend.app.db.models import DatabaseType, DBConfig

__all__ = [
    "DatabaseExecutor",
    "execute_query",
    "explain_query",
    "DBConfig",
    "DatabaseType",
]
