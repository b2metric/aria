"""Producer writes pipeline events into run_store; tailer reads them back."""

from __future__ import annotations

import asyncio
import json

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from backend.app.api import query as query_api
from backend.app.query import run_store

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def redis():
    r = FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


async def _fake_pipeline(*args, **kwargs):
    yield {"event": "status", "data": json.dumps({"status": "thinking"})}
    yield {"event": "sql", "data": json.dumps({"sql": "SELECT 1"})}
    yield {"event": "done", "data": json.dumps({"conversation_id": "cid-1"})}


async def test_run_producer_writes_all_events_and_marks_complete(redis, monkeypatch):
    monkeypatch.setattr(query_api, "process_query", _fake_pipeline)
    await run_store.acquire_run(redis, "cid-1", "run-a")

    await query_api._run_producer(
        redis=redis,
        engine=None,
        body=None,
        workspace_id="ws",
        user_id="u",
        team_id=None,
        sql_visible=True,
        cid="cid-1",
    )

    events, _ = await run_store.read_events(redis, "cid-1", "0", block_ms=0)
    assert [e["event"] for e in events] == ["status", "sql", "done"]
    assert await run_store.get_status(redis, "cid-1") == "complete"


async def test_run_producer_records_error_event_on_exception(redis, monkeypatch):
    async def _boom(*a, **k):
        yield {"event": "status", "data": "{}"}
        raise RuntimeError("kaboom")

    monkeypatch.setattr(query_api, "process_query", _boom)
    await run_store.acquire_run(redis, "cid-2", "run-b")

    await query_api._run_producer(
        redis=redis,
        engine=None,
        body=None,
        workspace_id="ws",
        user_id="u",
        team_id=None,
        sql_visible=True,
        cid="cid-2",
    )

    events, _ = await run_store.read_events(redis, "cid-2", "0", block_ms=0)
    assert events[-1]["event"] == "error"
    assert "kaboom" in events[-1]["data"]
    assert await run_store.get_status(redis, "cid-2") == "error"


async def test_run_producer_maintains_heartbeat_for_run_id(redis, monkeypatch):
    """The detached POST producer must keep its run lock alive via a heartbeat
    task for the lifetime of generation, then stop it on completion."""
    monkeypatch.setattr(query_api, "process_query", _fake_pipeline)
    seen: dict = {}

    async def _fake_heartbeat(r, cid, run_id, *a, **k):
        seen["cid"] = cid
        seen["run_id"] = run_id
        await asyncio.sleep(3600)  # block until the producer cancels it

    monkeypatch.setattr(run_store, "maintain_heartbeat", _fake_heartbeat)
    await run_store.acquire_run(redis, "cid-hb", "run-hb")

    await query_api._run_producer(
        redis=redis,
        engine=None,
        body=None,
        workspace_id="ws",
        user_id="u",
        team_id=None,
        sql_visible=True,
        cid="cid-hb",
        run_id="run-hb",
    )

    # Heartbeat was started against this run, and the run still completed (the
    # heartbeat task was cancelled cleanly when generation finished).
    assert seen == {"cid": "cid-hb", "run_id": "run-hb"}
    assert await run_store.get_status(redis, "cid-hb") == "complete"


# ── POST /api/query integration: spawn producer + tail the run stream ──────
#
# JWT fixtures are copied verbatim from backend/tests/test_query.py so this
# module is self-contained (cross-module fixture import proved fragile).

import base64  # noqa: E402
import time  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

from cryptography.hazmat.backends import default_backend  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fakeredis import FakeServer  # noqa: E402
from fakeredis.aioredis import FakeRedis as AioFakeRedis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt as jose_jwt  # noqa: E402


@pytest.fixture(scope="session")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())


@pytest.fixture(scope="session")
def jwks(rsa_key):
    pub_numbers = rsa_key.public_key().public_numbers()

    def _b64url_int(n: int) -> str:
        n_bytes = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_int(pub_numbers.n),
                "e": _b64url_int(pub_numbers.e),
            }
        ]
    }


@pytest.fixture
def auth_token(rsa_key):
    now = int(time.time())
    payload = {
        "sub": "test-user-uuid",
        "iss": "http://localhost:8080/realms/aria",
        "aud": "aria-backend",
        "exp": now + 3600,
        "iat": now,
        "workspace_id": "ws-test-001",
        "user_id": "user-001",
        "team_id": "team-001",
        "role": "analyst",
        "email": "test@b2metric.com",
        "name": "Test User",
        "preferred_username": "testuser",
    }
    return jose_jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": "test-kid"})


# Sync test: TestClient drives its own anyio portal loop; the route's
# asyncio.create_task producer runs on the app's loop. The async form
# deadlocks the two loops, so this is intentionally a plain def (the
# module-level asyncio pytestmark is a no-op on a non-coroutine test).
def test_post_query_creates_run_and_streams(auth_token, jwks):
    from backend.app.main import app

    server = FakeServer()
    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=jwks),
        patch.object(
            query_api,
            "_get_redis",
            AsyncMock(
                side_effect=lambda *a, **k: AioFakeRedis(server=server, decode_responses=True)
            ),
        ),
        patch.object(query_api, "_get_engine", AsyncMock(return_value=AsyncMock())),
        patch.object(query_api, "_resolve_sql_visible", AsyncMock(return_value=True)),
        patch.object(query_api, "check_rate_limit", AsyncMock(return_value=None)),
        patch.object(query_api, "process_query", _fake_pipeline),
    ):
        client = TestClient(app)
        with client.stream(
            "POST",
            "/api/query",
            json={"question": "Show monthly revenue by region"},
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            assert resp.status_code == 200
            body = b""
            for chunk in resp.iter_bytes():
                body += chunk
                if b"done" in body:
                    break

        # The tailed response carries the pipeline events through the stream.
        assert b"sql" in body and b"done" in body

        # The route must have driven generation through the durable run store
        # (this is what distinguishes the producer/tailer path from streaming
        # process_query directly): a run record exists and is terminal, and the
        # stream replays the events. We read with a fresh connection on the
        # SAME shared server, exactly as a reconnecting client would.
        async def _assert_run_recorded():
            r = AioFakeRedis(server=server, decode_responses=True)
            try:
                # Exactly one conversation was created → find its run stream.
                stream_keys = await r.keys(f"{run_store.STREAM_PREFIX}*")
                assert len(stream_keys) == 1
                cid = stream_keys[0][len(run_store.STREAM_PREFIX) :]
                assert await run_store.get_status(r, cid) == run_store.COMPLETE
                events, _ = await run_store.read_events(r, cid, "0", block_ms=0)
                assert [e["event"] for e in events] == ["status", "sql", "done"]
            finally:
                await r.aclose()

        asyncio.run(_assert_run_recorded())


# The auth_token fixture encodes user_id="user-001" / workspace_id="ws-test-001";
# the ownership gate compares conv.user_id to the caller's user_id.
_OWNER_ID = "user-001"
_OWNER_WS = "ws-test-001"


async def _save_owned_conversation(server, cid: str, *, owner: str = _OWNER_ID) -> None:
    """Persist a Conversation row so the ownership gate on the GET endpoints
    resolves (owner match → 200, mismatch → 404)."""
    from backend.app.query import Conversation
    from backend.app.query.conversation import save_conversation

    r = AioFakeRedis(server=server, decode_responses=True)
    try:
        conv = Conversation(id=cid, workspace_id=_OWNER_WS, user_id=owner)
        await save_conversation(r, conv)
    finally:
        await r.aclose()


# ── GET /api/query/{cid}/status ────────────────────────────────────────────
#
# Sync test (TestClient drives its own loop); run-state setup/transitions are
# applied with asyncio.run() helpers on a connection over the SAME FakeServer.
def test_status_endpoint_reports_running_then_done(auth_token, jwks):
    from backend.app.main import app

    server = FakeServer()

    async def _acquire():
        r = AioFakeRedis(server=server, decode_responses=True)
        await run_store.acquire_run(r, "cid-9", "run-x")
        await r.aclose()

    async def _finish():
        r = AioFakeRedis(server=server, decode_responses=True)
        await run_store.finish_run(r, "cid-9", "complete")
        await r.aclose()

    asyncio.run(_save_owned_conversation(server, "cid-9"))
    asyncio.run(_acquire())

    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=jwks),
        patch.object(
            query_api,
            "_get_redis",
            AsyncMock(
                side_effect=lambda *a, **k: AioFakeRedis(server=server, decode_responses=True)
            ),
        ),
    ):
        client = TestClient(app)
        h = {"Authorization": f"Bearer {auth_token}"}

        r1 = client.get("/api/query/cid-9/status", headers=h)
        assert r1.status_code == 200 and r1.json()["status"] == "running"

        asyncio.run(_finish())

        r2 = client.get("/api/query/cid-9/status", headers=h)
        assert r2.json()["status"] == "complete"

        # Unknown conversation → 404 (ownership gate, does not confirm existence).
        r3 = client.get("/api/query/unknown/status", headers=h)
        assert r3.status_code == 404


def test_get_endpoints_reject_non_owner_with_404(auth_token, jwks):
    """A run owned by another user must NOT be readable (status or stream).

    The gate returns 404 (not 403) so it never confirms the cid exists.
    """
    from backend.app.main import app

    server = FakeServer()

    async def _setup():
        r = AioFakeRedis(server=server, decode_responses=True)
        await run_store.acquire_run(r, "cid-other", "run-o")
        await run_store.append_event(r, "cid-other", {"event": "sql", "data": '{"sql":"SECRET"}'})
        await run_store.finish_run(r, "cid-other", "complete")
        await r.aclose()

    # Conversation is owned by somebody else, not the token's user-001.
    asyncio.run(_save_owned_conversation(server, "cid-other", owner="someone-else"))
    asyncio.run(_setup())

    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=jwks),
        patch.object(
            query_api,
            "_get_redis",
            AsyncMock(
                side_effect=lambda *a, **k: AioFakeRedis(server=server, decode_responses=True)
            ),
        ),
    ):
        client = TestClient(app)
        h = {"Authorization": f"Bearer {auth_token}"}

        assert client.get("/api/query/cid-other/status", headers=h).status_code == 404

        with client.stream("GET", "/api/query/cid-other/stream", headers=h) as resp:
            assert resp.status_code == 404
            # The gated SQL event must never reach a non-owner.
            assert b"SECRET" not in resp.read()


# ── GET /api/query/{cid}/stream (resume/tail) ──────────────────────────────
#
# Sync test: a run is pre-populated (buffered events + terminal status) on a
# shared FakeServer; the resume endpoint must replay the whole buffer.
def test_resume_stream_replays_buffered_events(auth_token, jwks):
    from backend.app.main import app

    server = FakeServer()

    async def _populate():
        r = AioFakeRedis(server=server, decode_responses=True)
        await run_store.acquire_run(r, "cid-7", "run-7")
        await run_store.append_event(
            r, "cid-7", {"event": "status", "data": '{"status":"thinking"}'}
        )
        await run_store.append_event(r, "cid-7", {"event": "sql", "data": '{"sql":"SELECT 1"}'})
        await run_store.append_event(r, "cid-7", {"event": "done", "data": "{}"})
        await run_store.finish_run(r, "cid-7", "complete")
        await r.aclose()

    asyncio.run(_save_owned_conversation(server, "cid-7"))
    asyncio.run(_populate())

    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=jwks),
        patch.object(
            query_api,
            "_get_redis",
            AsyncMock(
                side_effect=lambda *a, **k: AioFakeRedis(server=server, decode_responses=True)
            ),
        ),
    ):
        client = TestClient(app)
        with client.stream(
            "GET",
            "/api/query/cid-7/stream",
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            assert resp.status_code == 200
            body = b""
            for chunk in resp.iter_bytes():
                body += chunk
                if b"done" in body:
                    break

    assert b"thinking" in body and b"SELECT 1" in body and b"done" in body


# ── _tail_events termination on unknown/expired cid ────────────────────────


class _NeverDisconnected:
    """Minimal Request stand-in: never reports the client as disconnected."""

    async def is_disconnected(self) -> bool:
        return False


async def test_tail_events_terminates_on_unknown_cid(redis, monkeypatch):
    """A cid with no stream and no run record must not loop forever.

    ``read_events`` is patched to non-blocking (block_ms=0) so the test does not
    pay the production 15s XREAD block; the behaviour under test is that an empty
    read + ``status is None`` terminates the loop rather than spinning forever.
    """
    real_read_events = run_store.read_events

    async def _nonblocking_read(r, c, last_id="0", block_ms=15000):
        return await real_read_events(r, c, last_id, block_ms=0)

    monkeypatch.setattr(run_store, "read_events", _nonblocking_read)

    collected = [
        event async for event in query_api._tail_events(redis, "no-such-run", _NeverDisconnected())
    ]
    assert collected == []


# ── Producer marks run terminal (ERROR) on cancellation ────────────────────


async def test_run_producer_marks_error_and_reraises_on_cancel(redis, monkeypatch):
    """If the detached producer task is cancelled mid-flight, the run must not
    be left RUNNING forever — it is marked ERROR and CancelledError re-raised."""

    async def _hangs(*a, **k):
        yield {"event": "status", "data": "{}"}
        await asyncio.sleep(3600)  # block until cancelled

    monkeypatch.setattr(query_api, "process_query", _hangs)
    await run_store.acquire_run(redis, "cid-cancel", "run-c")

    task = asyncio.create_task(
        query_api._run_producer(
            redis=redis,
            engine=None,
            body=None,
            workspace_id="ws",
            user_id="u",
            team_id=None,
            sql_visible=True,
            cid="cid-cancel",
        )
    )
    # Let the producer start and append its first event, then cancel it.
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert await run_store.get_status(redis, "cid-cancel") == "error"
