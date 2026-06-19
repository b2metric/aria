"""Database configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DatabaseType(StrEnum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    MSSQL = "mssql"


@dataclass
class DBConfig:
    """Database connection configuration.

    Attributes:
        db_type: Database type (postgresql, mysql, oracle, mssql)
        host: Database host
        port: Database port
        database: Database name (or service name for Oracle)
        username: Connection username
        password: Connection password (decrypted)
        options: Additional connection options (SSL, timeout, etc.)
        max_row_limit: Maximum allowed rows for this tenant
    """

    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    options: dict[str, Any] | None = None
    max_row_limit: int = 1000

    @property
    def default_port(self) -> int:
        """Return default port for the database type."""
        return {
            DatabaseType.POSTGRESQL: 5432,
            DatabaseType.MYSQL: 3306,
            DatabaseType.ORACLE: 1521,
            DatabaseType.MSSQL: 1433,
        }.get(self.db_type, 5432)

    def get_port(self) -> int:
        """Return configured port or default."""
        return self.port or self.default_port
