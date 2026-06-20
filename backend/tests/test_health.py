"""Tests for the admin health endpoint helpers (Sprint 14 Task 3)."""

from __future__ import annotations

import pytest

from backend.app.api.endpoints.admin.health import _check_background_worker


@pytest.mark.asyncio
async def test_background_worker_check_reports_healthy() -> None:
    """The in-process asyncio worker probe completes and reports healthy.

    The large-result export is fire-and-forget via ``asyncio.create_task``;
    the probe verifies the event loop can schedule + finish a background task.
    """
    result = await _check_background_worker()

    assert result["status"] == "healthy"
    assert isinstance(result["latency_ms"], int)
    assert result["latency_ms"] >= 0
    assert "error" not in result
