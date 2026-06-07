"""Tests for the generic database executor module."""

from __future__ import annotations

import pytest

from backend.app.db import DBConfig, DatabaseType
from backend.app.db.executor import (
    PostgreSQLExecutor,
    MySQLExecutor,
    OracleExecutor,
    MSSQLExecutor,
    get_executor,
)


class TestDBConfig:
    """Tests for DBConfig dataclass."""
    
    def test_default_port_postgresql(self):
        config = DBConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=0,
            database="test",
            username="user",
            password="pass",
        )
        assert config.default_port == 5432
        assert config.get_port() == 5432
    
    def test_default_port_mysql(self):
        config = DBConfig(
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=0,
            database="test",
            username="user",
            password="pass",
        )
        assert config.default_port == 3306
    
    def test_default_port_oracle(self):
        config = DBConfig(
            db_type=DatabaseType.ORACLE,
            host="localhost",
            port=0,
            database="FREEPDB1",
            username="user",
            password="pass",
        )
        assert config.default_port == 1521
    
    def test_default_port_mssql(self):
        config = DBConfig(
            db_type=DatabaseType.MSSQL,
            host="localhost",
            port=0,
            database="test",
            username="user",
            password="pass",
        )
        assert config.default_port == 1433
    
    def test_custom_port(self):
        config = DBConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5433,
            database="test",
            username="user",
            password="pass",
        )
        assert config.get_port() == 5433


class TestGetExecutor:
    """Tests for executor factory."""
    
    def test_get_postgresql_executor(self):
        config = DBConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass",
        )
        executor = get_executor(config)
        assert isinstance(executor, PostgreSQLExecutor)
    
    def test_get_mysql_executor(self):
        config = DBConfig(
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            database="test",
            username="user",
            password="pass",
        )
        executor = get_executor(config)
        assert isinstance(executor, MySQLExecutor)
    
    def test_get_oracle_executor(self):
        config = DBConfig(
            db_type=DatabaseType.ORACLE,
            host="localhost",
            port=1521,
            database="FREEPDB1",
            username="user",
            password="pass",
        )
        executor = get_executor(config)
        assert isinstance(executor, OracleExecutor)
    
    def test_get_mssql_executor(self):
        config = DBConfig(
            db_type=DatabaseType.MSSQL,
            host="localhost",
            port=1433,
            database="test",
            username="user",
            password="pass",
        )
        executor = get_executor(config)
        assert isinstance(executor, MSSQLExecutor)


class TestDatabaseType:
    """Tests for DatabaseType enum."""
    
    def test_enum_values(self):
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.MYSQL.value == "mysql"
        assert DatabaseType.ORACLE.value == "oracle"
        assert DatabaseType.MSSQL.value == "mssql"
    
    def test_enum_is_str(self):
        # DatabaseType inherits from str
        assert isinstance(DatabaseType.POSTGRESQL, str)
        assert DatabaseType.ORACLE == "oracle"
