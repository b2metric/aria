import pytest
from backend.app.query.guards import verify_read_only_sql

def test_verify_read_only_sql_allowed():
    verify_read_only_sql("SELECT * FROM users")
    verify_read_only_sql("   SELECT id, name FROM customers WHERE active = 1")
    verify_read_only_sql("WITH cte AS (SELECT * FROM a) SELECT * FROM cte")
    verify_read_only_sql("EXPLAIN PLAN FOR SELECT * FROM tables")
    verify_read_only_sql("SELECT 'UPDATE table' FROM users")
    verify_read_only_sql("SELECT 'DELETE from everything' as info FROM dual")
    verify_read_only_sql("SELECT * FROM users -- DELETE EVERYTHING\nWHERE id = 1")
    verify_read_only_sql("SELECT * FROM users /* UPDATE all */ WHERE id = 1")

def test_verify_read_only_sql_blocked():
    with pytest.raises(ValueError, match="Unsafe SQL keyword"):
        verify_read_only_sql("UPDATE users SET active = 0")
    with pytest.raises(ValueError, match="Unsafe SQL keyword"):
        verify_read_only_sql("DELETE FROM users WHERE id = 1")
    with pytest.raises(ValueError, match="Unsafe SQL keyword"):
        verify_read_only_sql("DROP TABLE users")
    with pytest.raises(ValueError, match="must begin with SELECT or WITH"):
        verify_read_only_sql("SHOW TABLES")

def test_verify_read_only_sql_empty():
    with pytest.raises(ValueError, match="Empty SQL query"):
        verify_read_only_sql("")
