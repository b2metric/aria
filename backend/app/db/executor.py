"""Generic database query executor for PostgreSQL, MySQL, Oracle, MSSQL.

This module provides a unified interface for executing SQL queries across
different database backends. Each backend uses its native driver for optimal
performance and compatibility.

Usage:
    from backend.app.db import execute_query, DBConfig, DatabaseType

    config = DBConfig(
        db_type=DatabaseType.ORACLE,
        host="localhost",
        port=1521,
        database="FREEPDB1",
        username="stc",
        password="stc123",
    )

    rows = await execute_query("SELECT * FROM employees WHERE dept = :dept", config, {"dept": "HR"})
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.db.models import DatabaseType, DBConfig

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Oracle Thick Mode Initialization
# ══════════════════════════════════════════════════════════════════════════════

_oracle_thick_initialized = False


def _init_oracle_thick_mode() -> None:
    """Initialize Oracle thick mode (once per process).

    Thick mode is required for advanced Oracle features:
    - LDAP/OID authentication
    - Kerberos authentication
    - Oracle Net features (encryption, compression)
    - Some data types (BFILE, REF CURSOR)
    """
    global _oracle_thick_initialized
    if _oracle_thick_initialized:
        return

    import os

    import oracledb

    from backend.app.core.config import get_settings

    settings = get_settings()
    lib_dir = settings.oracle_client_lib_dir

    if lib_dir:
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
            logger.info("Oracle thick mode initialized from config: %s", lib_dir)
            _oracle_thick_initialized = True
            return
        except oracledb.ProgrammingError as e:
            if "already been called" in str(e):
                _oracle_thick_initialized = True
                return
            raise

    # Try default locations
    default_paths = [
        "/opt/oracle",  # macOS direct install
        "/opt/oracle/instantclient",  # Docker container
        "/opt/oracle/instantclient_23_3",
        "/opt/oracle/instantclient_21_3",
        os.path.expanduser("~/instantclient_23_3"),
        os.path.expanduser("~/instantclient_21_3"),
    ]

    for path in default_paths:
        if os.path.exists(path):
            try:
                oracledb.init_oracle_client(lib_dir=path)
                logger.info("Oracle thick mode initialized: %s", path)
                _oracle_thick_initialized = True
                return
            except oracledb.ProgrammingError as e:
                if "already been called" in str(e):
                    _oracle_thick_initialized = True
                    return
                continue

    logger.warning("Oracle Instant Client not found, using thin mode")
    _oracle_thick_initialized = True


# ══════════════════════════════════════════════════════════════════════════════
# Database Executors
# ══════════════════════════════════════════════════════════════════════════════


class DatabaseExecutor:
    """Base class for database executors."""

    def __init__(self, config: DBConfig):
        self.config = config

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute SQL and return results as list of dicts."""
        raise NotImplementedError

    def explain(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Explain SQL and return estimated rows and cost."""
        return {"estimated_rows": 0, "estimated_cost": 0, "raw": None}


class PostgreSQLExecutor(DatabaseExecutor):
    """PostgreSQL executor using psycopg2."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.get_port(),
            dbname=self.config.database,
            user=self.config.username,
            password=self.config.password,
            **(self.config.options or {}),
        )
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or {})
                if cur.description:
                    return [dict(row) for row in cur.fetchall()]
                return []
        finally:
            conn.close()

    def explain(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Explain PostgreSQL query to get row estimates."""

        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.get_port(),
            dbname=self.config.database,
            user=self.config.username,
            password=self.config.password,
            **(self.config.options or {}),
        )
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Use JSON format for reliable parsing
                explain_sql = f"EXPLAIN (FORMAT JSON) {sql}"
                cur.execute(explain_sql, params or {})
                res = cur.fetchone()
                if res and "QUERY PLAN" in res:
                    plan = res["QUERY PLAN"][0]["Plan"]
                    rows = plan.get("Plan Rows", 0)
                    cost = plan.get("Total Cost", 0)
                    return {"estimated_rows": rows, "estimated_cost": cost, "raw": plan}
                return {"estimated_rows": 0, "estimated_cost": 0, "raw": None}
        finally:
            conn.close()


class MySQLExecutor(DatabaseExecutor):
    """MySQL executor using pymysql."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        import pymysql
        import pymysql.cursors

        conn = pymysql.connect(
            host=self.config.host,
            port=self.config.get_port(),
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            cursorclass=pymysql.cursors.DictCursor,
            **(self.config.options or {}),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or {})
                if cur.description:
                    return list(cur.fetchall())
                return []
        finally:
            conn.close()

    def explain(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Estimate rows via MySQL ``EXPLAIN`` so the massive-query guard works.

        Without this override MySQL inherited the no-op base (estimated_rows=0),
        which silently disabled the pre-execution row guard. We take the max
        per-table ``rows`` estimate as a conservative single-scan proxy.
        """
        import pymysql
        import pymysql.cursors

        conn = pymysql.connect(
            host=self.config.host,
            port=self.config.get_port(),
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            cursorclass=pymysql.cursors.DictCursor,
            **(self.config.options or {}),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(f"EXPLAIN {sql}", params or {})
                rows = cur.fetchall() or []
                est = max((int(r.get("rows") or 0) for r in rows), default=0)
                return {"estimated_rows": est, "estimated_cost": 0, "raw": list(rows)}
        finally:
            conn.close()


class OracleExecutor(DatabaseExecutor):
    """Oracle executor using oracledb (thin mode by default, thick if client available)."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        import oracledb

        # Try thick mode only if explicitly configured
        from backend.app.core.config import get_settings

        settings = get_settings()
        if settings.oracle_client_lib_dir:
            _init_oracle_thick_mode()

        # Build DSN
        dsn = f"{self.config.host}:{self.config.get_port()}/{self.config.database}"

        conn = oracledb.connect(
            user=self.config.username,
            password=self.config.password,
            dsn=dsn,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or {})
                if cur.description:
                    columns = [d[0] for d in cur.description]
                    return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]
                return []
        finally:
            conn.close()

    def explain(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Explain Oracle query to get row estimates."""

        import oracledb

        from backend.app.core.config import get_settings

        settings = get_settings()
        if settings.oracle_client_lib_dir:
            _init_oracle_thick_mode()

        dsn = f"{self.config.host}:{self.config.get_port()}/{self.config.database}"
        conn = oracledb.connect(
            user=self.config.username,
            password=self.config.password,
            dsn=dsn,
        )
        try:
            with conn.cursor() as cur:
                # Oracle EXPLAIN PLAN puts results in PLAN_TABLE
                import time

                stmt_id = f"aria_explain_{int(time.time())}"
                explain_sql = f"EXPLAIN PLAN SET STATEMENT_ID = '{stmt_id}' FOR {sql}"
                cur.execute(explain_sql, params or {})

                cur.execute(
                    f"SELECT CARDINALITY, COST FROM PLAN_TABLE WHERE STATEMENT_ID = '{stmt_id}' AND ID = 0"
                )
                res = cur.fetchone()

                # Clean up plan table
                try:
                    cur.execute(f"DELETE FROM PLAN_TABLE WHERE STATEMENT_ID = '{stmt_id}'")
                    conn.commit()
                except Exception:
                    pass

                if res:
                    return {
                        "estimated_rows": res[0] or 0,
                        "estimated_cost": res[1] or 0,
                        "raw": None,
                    }
                return {"estimated_rows": 0, "estimated_cost": 0, "raw": None}
        finally:
            conn.close()


class MSSQLExecutor(DatabaseExecutor):
    """Microsoft SQL Server executor using pymssql."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        import pymssql

        conn = pymssql.connect(
            server=self.config.host,
            port=str(self.config.get_port()),
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            as_dict=True,
            **(self.config.options or {}),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or {})
                if cur.description:
                    return list(cur.fetchall())
                return []
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Factory & Public API
# ══════════════════════════════════════════════════════════════════════════════

_EXECUTORS: dict[DatabaseType, type[DatabaseExecutor]] = {
    DatabaseType.POSTGRESQL: PostgreSQLExecutor,
    DatabaseType.MYSQL: MySQLExecutor,
    DatabaseType.ORACLE: OracleExecutor,
    DatabaseType.MSSQL: MSSQLExecutor,
}


def get_executor(config: DBConfig) -> DatabaseExecutor:
    """Get the appropriate executor for the database type."""
    executor_class = _EXECUTORS.get(config.db_type)
    if not executor_class:
        raise ValueError(f"Unsupported database type: {config.db_type}")
    return executor_class(config)


def explain_query_sync(
    sql: str,
    config: DBConfig,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain a SQL query synchronously.

    Honors `ARIA_SKIP_EXPLAIN=1` to bypass the cost-estimate round-trip entirely
    — useful for remote databases (e.g. STC Oracle over VPN) where the extra
    connect + 4 EXPLAIN statements add several seconds per request. The
    pipeline's safety guards (`FETCH FIRST N ROWS ONLY`, row-limit cap on
    fetched results) remain in effect.
    """
    import os

    if os.environ.get("ARIA_SKIP_EXPLAIN") == "1":
        return {"estimated_rows": 0, "estimated_cost": 0, "raw": None, "skipped": True}

    executor = get_executor(config)
    return executor.explain(sql, params)


async def explain_query(
    sql: str,
    config: DBConfig,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain a SQL query asynchronously.

    Args:
        sql: SQL query string
        config: Database configuration
        params: Query parameters (optional)

    Returns:
        Dict containing estimated_rows, estimated_cost
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: explain_query_sync(sql, config, params),
    )


def execute_query_sync(
    sql: str,
    config: DBConfig,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a SQL query synchronously.

    Args:
        sql: SQL query string
        config: Database configuration
        params: Query parameters (optional)

    Returns:
        List of dicts, each representing a row

    Raises:
        ValueError: If database type is not supported
        Various DB driver exceptions on connection/query errors
    """
    executor = get_executor(config)
    logger.debug(
        "Executing query on %s://%s:%d/%s",
        config.db_type.value,
        config.host,
        config.get_port(),
        config.database,
    )
    return executor.execute(sql, params)


async def execute_query(
    sql: str,
    config: DBConfig,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a SQL query asynchronously (runs sync executor in thread pool).

    Args:
        sql: SQL query string
        config: Database configuration
        params: Query parameters (optional)

    Returns:
        List of dicts, each representing a row
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: execute_query_sync(sql, config, params),
    )
