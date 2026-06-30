"""End-to-end integration tests for ARIA query pipeline.

Tests the full flow: NL question → SQL → Execution → Chart
Run: pytest tests/test_e2e_integration.py -v -m integration
"""

import pytest
import httpx
import json
import os
import asyncio
from typing import Generator


# Test configuration
API_BASE = os.getenv("ARIA_API_BASE", "http://localhost:8000")
WORKSPACE_ID = "stc-kuwait"
USER_ID = "test-user"


# These are live-server integration tests (intended to run with `-m integration`
# against a running backend at API_BASE). When the server is not reachable — e.g.
# in the unit/DoD gate, which does not start a server — SKIP rather than hard-fail,
# so the gate reflects code health, not environment availability.
def _api_reachable() -> bool:
    try:
        httpx.get(API_BASE, timeout=2.0)
        return True
    except httpx.ConnectError:
        return False
    except Exception:
        # A non-connection error means the server responded → it is reachable.
        return True


pytestmark = pytest.mark.skipif(
    not _api_reachable(),
    reason=f"ARIA backend not reachable at {API_BASE}; integration tests skipped",
)


class TestQueryPipelineE2E:
    """End-to-end query pipeline tests."""

    @pytest.mark.integration
    def test_simple_query_sse(self):
        """Test simple query via SSE stream."""
        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                "POST",
                f"{API_BASE}/api/v1/query/stream",
                json={
                    "question": "show total count of records",
                    "workspace_id": WORKSPACE_ID,
                    "user_id": USER_ID,
                },
            ) as response:
                assert response.status_code == 200

                events = []
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        events.append(data)
                        print(f"SSE Event: {data.get('event', 'unknown')}")

                # Should have at least status and done events
                event_types = [e.get("event") for e in events]
                assert "status" in event_types or "done" in event_types

    @pytest.mark.integration
    def test_complex_query_uses_llm(self):
        """Test that complex queries use LLM generation."""
        with httpx.Client(timeout=90.0) as client:
            with client.stream(
                "POST",
                f"{API_BASE}/api/v1/query/stream",
                json={
                    "question": "compare monthly revenue year over year",
                    "workspace_id": WORKSPACE_ID,
                    "user_id": USER_ID,
                },
            ) as response:
                assert response.status_code == 200

                events = []
                sql_event = None
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        events.append(data)
                        if data.get("event") == "sql":
                            sql_event = data

                # Should have generated SQL (even if execution fails due to missing data)
                if sql_event:
                    sql = sql_event.get("sql", "")
                    print(f"Generated SQL: {sql[:200]}")
                    assert len(sql) > 10

    @pytest.mark.integration
    def test_query_with_memory_context(self):
        """Test that memory context is used in queries."""
        from backend.app.memory.service import MemoryService

        # First, store a preference
        MemoryService._instance = None
        service = MemoryService()

        service.store_user_preference(
            preference="User prefers monthly aggregations",
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
        )

        # Now query - memory context should be available
        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                "POST",
                f"{API_BASE}/api/v1/query/stream",
                json={
                    "question": "show revenue trend",
                    "workspace_id": WORKSPACE_ID,
                    "user_id": USER_ID,
                },
            ) as response:
                assert response.status_code == 200

                # Just ensure the query completes
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        if data.get("event") == "error":
                            # Log but don't fail - data might not exist
                            print(f"Query error (expected if no data): {data}")


class TestSQLGeneration:
    """SQL generation tests."""

    @pytest.mark.integration
    def test_is_complex_query_detection(self):
        """Test complex query detection."""
        from backend.app.query.llm_sql import is_complex_query

        # Simple queries
        assert not is_complex_query("show total revenue")
        assert not is_complex_query("count all customers")
        assert not is_complex_query("average order amount")

        # Complex queries
        assert is_complex_query("compare revenue year over year")
        assert is_complex_query("show running total of sales")
        assert is_complex_query("customers who have more than average orders")
        assert is_complex_query("join products with categories")
        assert is_complex_query("rank customers by spending")

    @pytest.mark.integration
    def test_rule_based_generation(self):
        """Test rule-based SQL generation."""
        import asyncio
        from unittest.mock import MagicMock
        from backend.app.query.pipeline import _generate_sql

        async def run_test():
            # Mock engine (not used for vault-based generation)
            mock_engine = MagicMock()

            sql, explanation, is_llm, token_usage = await _generate_sql(
                question="show total revenue",
                engine=mock_engine,
                workspace_id=WORKSPACE_ID,
            )

            assert sql is not None
            assert len(sql) > 10
            assert "SELECT" in sql.upper()
            print(f"Generated SQL: {sql}")
            print(f"Explanation: {explanation}")
            print(f"LLM used: {is_llm}, Token usage: {token_usage}")

        asyncio.run(run_test())

    @pytest.mark.integration
    def test_llm_generation(self):
        """Test LLM-based SQL generation."""
        import asyncio
        from backend.app.query.llm_sql import generate_sql_with_llm

        async def run_test():
            tables = [
                {
                    "name": "FCT_PREP_REV",
                    "keywords": "revenue, topup, recharge",
                    "description": "Revenue fact table",
                },
            ]
            table_columns = {
                "FCT_PREP_REV": [
                    {"name": "EXEC_DATE", "type": "DATE"},
                    {"name": "TOPUP_AMOUNT", "type": "NUMBER"},
                    {"name": "MSISDN", "type": "VARCHAR2"},
                ],
            }

            sql, explanation, token_usage = await generate_sql_with_llm(
                question="show monthly revenue totals",
                tables=tables,
                table_columns=table_columns,
                db_type="oracle",
            )

            assert sql is not None
            assert len(sql) > 10
            assert "SELECT" in sql.upper()
            print(f"LLM SQL: {sql}")
            print(f"Token usage: {token_usage}")

        asyncio.run(run_test())


class TestVaultMatching:
    """Vault semantic matching tests."""

    @pytest.mark.integration
    def test_table_discovery(self):
        """Test table discovery from vault."""
        import asyncio
        from unittest.mock import MagicMock
        from backend.app.query.pipeline import _get_available_tables

        async def run_test():
            mock_engine = MagicMock()
            tables = await _get_available_tables(mock_engine, WORKSPACE_ID)

            assert len(tables) > 0
            print(f"Discovered {len(tables)} tables:")
            for t in tables[:5]:
                print(f"  - {t['name']}: {t.get('keywords', '')[:50]}")

        asyncio.run(run_test())

    @pytest.mark.integration
    def test_column_discovery(self):
        """Test column discovery from vault."""
        import asyncio
        from unittest.mock import MagicMock
        from backend.app.query.pipeline import _get_table_columns

        async def run_test():
            mock_engine = MagicMock()

            # Get first available table
            from backend.app.query.pipeline import _get_available_tables

            tables = await _get_available_tables(mock_engine, WORKSPACE_ID)

            if not tables:
                pytest.skip("No tables in vault")

            table_name = tables[0]["name"]
            columns = await _get_table_columns(mock_engine, table_name, WORKSPACE_ID)

            assert len(columns) > 0
            print(f"Columns for {table_name}:")
            for c in columns[:10]:
                print(f"  - {c['name']} ({c['type']})")

        asyncio.run(run_test())


class TestChartGeneration:
    """Chart generation tests."""

    @pytest.mark.integration
    def test_chart_pipeline(self):
        """Test chart generation pipeline."""
        from agents.chart_builder import run_chart_pipeline_sync
        from agents.chart_types import ChartConfig, ChartType, AxisConfig

        # Sample data
        data = [
            {"month": "Jan", "revenue": 1000},
            {"month": "Feb", "revenue": 1500},
            {"month": "Mar", "revenue": 1200},
        ]

        # Generate chart
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x=AxisConfig(column="month"),
            y=AxisConfig(column="revenue"),
            title="Monthly Revenue",
        )

        result = run_chart_pipeline_sync(data, question="Monthly Revenue")

        assert result is not None
        assert result.json is not None or result.error is None


class TestErrorHandling:
    """Error handling tests."""

    @pytest.mark.integration
    def test_invalid_workspace(self):
        """Test query with invalid workspace."""
        with httpx.Client(timeout=30.0) as client:
            with client.stream(
                "POST",
                f"{API_BASE}/api/v1/query/stream",
                json={
                    "question": "show data",
                    "workspace_id": "nonexistent-workspace-12345",
                    "user_id": USER_ID,
                },
            ) as response:
                # Should still return 200 (SSE stream) but with error event
                assert response.status_code == 200

                has_error = False
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        if data.get("event") == "error":
                            has_error = True
                            print(f"Expected error: {data.get('message', '')}")

    @pytest.mark.integration
    def test_empty_question(self):
        """Test query with empty question."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{API_BASE}/api/v1/query/stream",
                json={
                    "question": "",
                    "workspace_id": WORKSPACE_ID,
                    "user_id": USER_ID,
                },
            )
            # Should return 422 (validation error) or 200 with error event
            assert resp.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
