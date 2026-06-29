"""Tests for the admin health endpoint helpers (Sprint 14 Task 3)."""

from __future__ import annotations

import pytest

from backend.app.api.endpoints.admin.health import _check_background_worker, _check_minio


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


# ── MinIO liveness probe ─────────────────────────────────────────────
#
# System Health never probed MinIO, so the object-store (chart/export artifacts)
# had no card. _check_minio mirrors the litellm liveness probe: an unauthenticated
# GET to MinIO's /minio/health/live, healthy on 200, never raising.


class _FakeResp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeClient:
    """Minimal httpx.AsyncClient stand-in for the probe."""

    def __init__(self, status: int = 200, raise_exc: Exception | None = None) -> None:
        self._status = status
        self._exc = raise_exc
        self.calls: list[str] = []

    async def get(self, url: str):  # noqa: ANN201
        self.calls.append(url)
        if self._exc is not None:
            raise self._exc
        return _FakeResp(self._status)


@pytest.mark.asyncio
async def test_minio_check_healthy_hits_liveness_endpoint() -> None:
    client = _FakeClient(status=200)
    result = await _check_minio(client, "minio:9000")

    assert result["status"] == "healthy"
    assert client.calls == ["http://minio:9000/minio/health/live"]
    assert isinstance(result["latency_ms"], int)
    assert result["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_minio_check_unhealthy_on_non_200() -> None:
    result = await _check_minio(_FakeClient(status=503), "minio:9000")

    assert result["status"] == "unhealthy"
    assert "503" in result["error"]


@pytest.mark.asyncio
async def test_minio_check_unhealthy_on_exception_never_raises() -> None:
    result = await _check_minio(_FakeClient(raise_exc=RuntimeError("conn refused")), "minio:9000")

    assert result["status"] == "unhealthy"
    assert "conn refused" in result["error"]
