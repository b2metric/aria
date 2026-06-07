"""Database module — multi-database connection and query execution."""

from backend.app.db.executor import DatabaseExecutor, execute_query
from backend.app.db.models import DBConfig, DatabaseType

__all__ = [
    "DatabaseExecutor",
    "execute_query",
    "DBConfig",
    "DatabaseType",
]
