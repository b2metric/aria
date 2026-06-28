# Client-Resumable Chat Streaming — Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A page refresh / tab reopen / network blip during SQL generation no longer loses the answer — the user reconnects and watches the in-flight turn finish live.

**Architecture:** The pipeline's SSE events become durable in a per-conversation **Redis Stream** (`aria:run:{cid}`). `POST /api/query` runs generation as a **detached asyncio task** (a "producer") that `XADD`s events to the stream and survives client disconnect; the HTTP response is just a **tailer** that `XREAD`s the stream. A new `GET /api/query/{cid}/stream` lets a reloaded page re-tail (replay buffered events + live). A `GET /api/query/{cid}/status` tells the frontend whether to resume or render history. A per-conversation lock prevents duplicate runs. (Deploy/restart durability via Prefect is **Plan 2**.)

**Tech Stack:** FastAPI, `sse-starlette`, `redis.asyncio` (Redis Streams: `XADD`/`XREAD`), pytest + `fakeredis`, Next.js (fetch-based `ReadableStream` SSE).

**Scope note:** This plan is the complete vertical slice (backend + frontend + smoke) that fixes the reported bug. It does NOT add Prefect or touch `docker-compose`. Generation still dies if the *producing backend worker itself* restarts mid-run — that gap is closed by Plan 2 (`2026-06-28-prefect-deploy-durable-runs.md`, to be written after this ships).

---

## File Structure

| File | Responsibility | New/Modify |
|------|----------------|-----------|
| `backend/app/query/run_store.py` | Durable run event log over Redis Streams: lock, append event, status, read/tail | **New** |
| `backend/app/api/query.py` | POST = spawn producer + tail; new `GET /{cid}/stream` (resume) + `GET /{cid}/status` | Modify |
| `backend/tests/test_run_store.py` | Unit tests for run_store | **New** |
| `backend/tests/test_query_resume.py` | Integration tests for resume/status endpoints + producer | **New** |
| `pyproject.toml` | Add `fakeredis` test dependency | Modify |
| `frontend/src/lib/api.ts` | `getRunStatus(cid)` + `streamResume(cid)` | Modify |
| `frontend/src/app/chat/page.tsx` | Extract reusable SSE consumer; resume on load when run is active | Modify |

**Key conventions used across tasks** (define once, reuse verbatim):

- Redis keys: stream `aria:run:{cid}`, meta hash `aria:run_meta:{cid}`, lock `aria:run_lock:{cid}`.
- Run statuses: `"running"`, `"complete"`, `"error"`.
- Stream/meta TTL after terminal: `STREAM_TTL_S = 3600`. Lock TTL: `LOCK_TTL_S = 300`.
- Event shape (unchanged from pipeline): `{"event": "<status|sql|chart|insight|error|done>", "data": "<json string>"}`.
- `_get_redis()` returns `Redis.from_url(..., decode_responses=True)` — so all Redis reads return `str`, not `bytes`.
- **pytest config:** the effective config is `pytest.ini` (it overrides `pyproject.toml`), with **asyncio STRICT mode** (no `asyncio_mode=auto`). Every `async def` test module MUST declare `pytestmark = pytest.mark.asyncio` after imports, or the async tests are not run. TestClient-based tests should stay **sync** functions (as in `backend/tests/test_query.py`); when such a test needs async run_store setup, drive it with a tiny `asyncio.run(_setup())` helper rather than making the test itself async. Run tests with plain `pytest backend/tests/<file> -v` (no `--cov` flag needed; pytest.ini sets addopts).

---

## Task 1: Add `fakeredis` test dependency

**Files:**
- Modify: `pyproject.toml` (the test/dev dependency group)

- [ ] **Step 1: Inspect the current dependency groups**

Run: `grep -nE "fakeredis|dependency-groups|\[project.optional|dev =|test =|^dependencies" pyproject.toml`
Expected: shows where deps live; `fakeredis` absent.

- [ ] **Step 2: Add `fakeredis` to the dev/test deps**

Add `"fakeredis>=2.21,<3"` to the existing test/dev dependency list (match the group the project already uses — e.g. `[dependency-groups] dev = [...]` or `[project.optional-dependencies] test = [...]`). Example if a `dev` group exists:

```toml
dev = [
    # ...existing entries...
    "fakeredis>=2.21,<3",
]
```

- [ ] **Step 3: Install and verify**

Run: `uv sync --group dev || uv pip install "fakeredis>=2.21,<3"`
Then: `python -c "from fakeredis.aioredis import FakeRedis; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "test: add fakeredis for Redis Streams run-store unit tests"
```

---

## Task 2: `run_store` — run lock + status meta

**Files:**
- Create: `backend/app/query/run_store.py`
- Test: `backend/tests/test_run_store.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_run_store.py
"""Unit tests for the durable run event log (Redis Streams)."""
from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from backend.app.query import run_store


@pytest.fixture
async def redis():
    r = FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


async def test_acquire_run_returns_true_first_time(redis):
    assert await run_store.acquire_run(redis, "cid-1", "run-a") is True
    assert await run_store.get_status(redis, "cid-1") == "running"


async def test_acquire_run_returns_false_while_locked(redis):
    assert await run_store.acquire_run(redis, "cid-1", "run-a") is True
    # A second run for the same conversation cannot start.
    assert await run_store.acquire_run(redis, "cid-1", "run-b") is False


async def test_finish_run_sets_terminal_status_and_releases_lock(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    await run_store.finish_run(redis, "cid-1", "complete")
    assert await run_store.get_status(redis, "cid-1") == "complete"
    # Lock released → a new run may start.
    assert await run_store.acquire_run(redis, "cid-1", "run-b") is True


async def test_get_status_none_when_unknown(redis):
    assert await run_store.get_status(redis, "nope") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_run_store.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.app.query.run_store` (or `AttributeError`).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/query/run_store.py
"""Durable run event log backed by Redis Streams.

A "run" is one assistant turn (one pipeline execution) for a conversation.
Its events are appended to a Redis Stream so any process can replay/tail them,
which is what makes an in-flight answer survive a client refresh.
"""
from __future__ import annotations

from redis.asyncio import Redis

STREAM_PREFIX = "aria:run:"
META_PREFIX = "aria:run_meta:"
LOCK_PREFIX = "aria:run_lock:"

LOCK_TTL_S = 300       # a producer must finish within this; safety against leaks
STREAM_TTL_S = 3600    # keep the event log ~1h after the run ends (replay window)

RUNNING = "running"
COMPLETE = "complete"
ERROR = "error"


def _stream_key(cid: str) -> str:
    return f"{STREAM_PREFIX}{cid}"


def _meta_key(cid: str) -> str:
    return f"{META_PREFIX}{cid}"


def _lock_key(cid: str) -> str:
    return f"{LOCK_PREFIX}{cid}"


async def acquire_run(redis: Redis, cid: str, run_id: str) -> bool:
    """Try to start a run for *cid*. Returns False if one is already active.

    Uses SET NX as a one-run-per-conversation lock so a refresh-triggered
    request can never start a duplicate generation.
    """
    acquired = await redis.set(_lock_key(cid), run_id, nx=True, ex=LOCK_TTL_S)
    if not acquired:
        return False
    await redis.hset(_meta_key(cid), mapping={"run_id": run_id, "status": RUNNING})
    await redis.expire(_meta_key(cid), STREAM_TTL_S)
    return True


async def finish_run(redis: Redis, cid: str, status: str) -> None:
    """Mark a run terminal (*complete* or *error*) and release its lock."""
    await redis.hset(_meta_key(cid), "status", status)
    await redis.expire(_meta_key(cid), STREAM_TTL_S)
    await redis.expire(_stream_key(cid), STREAM_TTL_S)
    await redis.delete(_lock_key(cid))


async def get_status(redis: Redis, cid: str) -> str | None:
    """Return the run status for *cid*, or None if there is no run record."""
    status = await redis.hget(_meta_key(cid), "status")
    return status  # decode_responses=True → already str | None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_run_store.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/run_store.py backend/tests/test_run_store.py
git commit -m "feat(query): run_store lock + status meta over Redis"
```

---

## Task 3: `run_store` — append + read events (stream)

**Files:**
- Modify: `backend/app/query/run_store.py`
- Test: `backend/tests/test_run_store.py`

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_run_store.py

async def test_append_and_read_events_replays_in_order(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    await run_store.append_event(redis, "cid-1", {"event": "status", "data": '{"status":"thinking"}'})
    await run_store.append_event(redis, "cid-1", {"event": "sql", "data": '{"sql":"SELECT 1"}'})

    events, last_id = await run_store.read_events(redis, "cid-1", "0", block_ms=0)

    assert [e["event"] for e in events] == ["status", "sql"]
    assert events[1]["data"] == '{"sql":"SELECT 1"}'
    assert last_id != "0"


async def test_read_events_from_last_id_returns_only_new(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    await run_store.append_event(redis, "cid-1", {"event": "status", "data": "{}"})
    first, last_id = await run_store.read_events(redis, "cid-1", "0", block_ms=0)

    await run_store.append_event(redis, "cid-1", {"event": "done", "data": "{}"})
    second, _ = await run_store.read_events(redis, "cid-1", last_id, block_ms=0)

    assert [e["event"] for e in second] == ["done"]


async def test_read_events_empty_when_nothing_new(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    events, last_id = await run_store.read_events(redis, "cid-1", "$", block_ms=0)
    assert events == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_run_store.py -k events -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'append_event'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/query/run_store.py`:

```python
async def append_event(redis: Redis, cid: str, event: dict) -> None:
    """Append one SSE event to the run's stream.

    *event* is the pipeline's event dict: {"event": str, "data": json-str}.
    """
    await redis.xadd(
        _stream_key(cid),
        {"event": event["event"], "data": event["data"]},
    )


async def read_events(
    redis: Redis, cid: str, last_id: str = "0", block_ms: int = 15000
) -> tuple[list[dict], str]:
    """Read events appended after *last_id*.

    ``last_id="0"`` replays the whole stream (used on connect/resume);
    a returned id fed back in tails only new events. ``block_ms`` blocks for
    that long waiting for new entries (0 = non-blocking, for tests).
    Returns (events, new_last_id). new_last_id is unchanged when nothing new.
    """
    result = await redis.xread({_stream_key(cid): last_id}, block=block_ms or None)
    if not result:
        return [], last_id
    # result: [(stream_key, [(entry_id, {field: val}), ...])]
    _key, entries = result[0]
    events = [{"event": fields["event"], "data": fields["data"]} for _id, fields in entries]
    new_last_id = entries[-1][0]
    return events, new_last_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_run_store.py -v`
Expected: PASS (7 passed total).

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/run_store.py backend/tests/test_run_store.py
git commit -m "feat(query): run_store append/read events via Redis Streams"
```

---

## Task 4: Producer + tailer helpers in the query API

**Files:**
- Modify: `backend/app/api/query.py` (add helpers above the `query` route; keep existing imports)
- Test: `backend/tests/test_query_resume.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_query_resume.py
"""Producer writes pipeline events into run_store; tailer reads them back."""
from __future__ import annotations

import json

import pytest
from fakeredis.aioredis import FakeRedis

from backend.app.api import query as query_api
from backend.app.query import run_store


@pytest.fixture
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
        redis=redis, engine=None, body=None, workspace_id="ws", user_id="u",
        team_id=None, sql_visible=True, cid="cid-1",
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
        redis=redis, engine=None, body=None, workspace_id="ws", user_id="u",
        team_id=None, sql_visible=True, cid="cid-2",
    )

    events, _ = await run_store.read_events(redis, "cid-2", "0", block_ms=0)
    assert events[-1]["event"] == "error"
    assert "kaboom" in events[-1]["data"]
    assert await run_store.get_status(redis, "cid-2") == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_query_resume.py -v`
Expected: FAIL — `AttributeError: module 'backend.app.api.query' has no attribute '_run_producer'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/api/query.py`, add `import asyncio` at the top with the other imports, then add these helpers after the existing `_resolve_sql_visible` function (before the `@router.post("/query"...)` route). Note `_run_producer` takes its OWN redis/engine when spawned for real (see Task 5); in tests `engine`/`body` are unused by the fake pipeline.

```python
# ── Durable run: producer + tailer ────────────────────────────────────────
from backend.app.query import run_store  # noqa: E402  (grouped with query imports)

# Hold strong references to detached producer tasks so they are not GC'd
# mid-flight (asyncio only keeps weak refs to bare tasks).
_PRODUCERS: set[asyncio.Task] = set()


async def _run_producer(
    *,
    redis: Redis,
    engine: AsyncEngine,
    body: QueryRequest,
    workspace_id: str,
    user_id: str,
    team_id: str | None,
    sql_visible: bool,
    cid: str,
) -> None:
    """Drive the (already SQL-visibility-gated) pipeline into the run stream.

    Runs detached from the HTTP request, so a client disconnect does not kill
    generation. Every event is appended to ``aria:run:{cid}``; the run is then
    marked terminal and its lock released.
    """
    try:
        async for event in process_query(
            redis=redis,
            engine=engine,
            request=body,
            workspace_id=workspace_id,
            user_id=user_id,
            team_id=team_id,
            sql_visible=sql_visible,
        ):
            await run_store.append_event(redis, cid, event)
        await run_store.finish_run(redis, cid, run_store.COMPLETE)
    except Exception as exc:  # noqa: BLE001 — surface as a terminal error event
        logger.exception("Producer failed for conversation %s", cid)
        await run_store.append_event(
            redis, cid, {"event": "error", "data": json.dumps({"error": str(exc)})}
        )
        await run_store.finish_run(redis, cid, run_store.ERROR)


async def _tail_events(redis: Redis, cid: str, request: Request):
    """Yield SSE events from the run stream until the run is terminal.

    Replays from the start (id ``0``) so a reconnecting client sees the whole
    in-flight turn, then live-tails. Stops on a ``done``/``error`` event, or
    when the run record is terminal and the stream is drained.
    """
    last_id = "0"
    while True:
        if await request.is_disconnected():
            return
        events, last_id = await run_store.read_events(redis, cid, last_id, block_ms=15000)
        for event in events:
            yield event
            if event["event"] in ("done", "error"):
                return
        if not events:
            status = await run_store.get_status(redis, cid)
            if status in (run_store.COMPLETE, run_store.ERROR):
                return
```

Also confirm `QueryRequest` is imported from `backend.app.query` near the top of the file (it is, at line ~21).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_query_resume.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/query.py backend/tests/test_query_resume.py
git commit -m "feat(query): detached run producer + stream tailer helpers"
```

---

## Task 5: Rewire `POST /api/query` to spawn producer + tail

**Files:**
- Modify: `backend/app/api/query.py` (the `query` route body, lines ~134-159)

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_query_resume.py
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

# Reuse the JWT key/jwks/token fixtures from the existing query suite.
from backend.tests.test_query import rsa_key, jwks, auth_token  # noqa: F401


@pytest.fixture
def _JWKS_VALUE(jwks):
    return jwks


async def test_post_query_creates_run_and_streams(monkeypatch, redis, auth_token, _JWKS_VALUE):
    """POST starts a run (lock acquired) and the response tails its events."""
    monkeypatch.setattr(query_api, "process_query", _fake_pipeline)

    from backend.app.main import app

    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=_JWKS_VALUE),
        patch.object(query_api, "_get_redis", AsyncMock(return_value=redis)),
        patch.object(query_api, "_get_engine", AsyncMock(return_value=AsyncMock())),
        patch.object(query_api, "_resolve_sql_visible", AsyncMock(return_value=True)),
        patch.object(query_api, "check_rate_limit", AsyncMock(return_value=None)),
    ):
        client = TestClient(app)
        with client.stream(
            "POST", "/api/query",
            json={"question": "Show monthly revenue by region"},
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            assert resp.status_code == 200
            body = b""
            for chunk in resp.iter_bytes():
                body += chunk
                if b"done" in body:
                    break
    assert b"sql" in body and b"done" in body
```

> If cross-module fixture import is awkward in this repo, copy the `rsa_key`/`jwks`/`auth_token` fixtures from `test_query.py` verbatim into `test_query_resume.py` instead.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_query_resume.py -k post_query -v`
Expected: FAIL — events not streamed (run never spawned) or `_run_producer` not invoked.

- [ ] **Step 3: Write minimal implementation**

Replace the body of the `query` route (currently lines ~129-159, from `engine = await _get_engine()` through `return EventSourceResponse(event_generator())`) with:

```python
    engine = await _get_engine()

    # Resolve the per-user SQL-visibility override (DB) over the role default.
    sql_visible = await _resolve_sql_visible(engine, user)

    # Ensure we have a conversation id BEFORE spawning the producer, so the run
    # stream/lock can be keyed on it. A brand-new conversation is created empty
    # here; process_query() then loads it and appends the user message (no dup).
    cid = body.conversation_id
    if not cid:
        from backend.app.query import Conversation
        from backend.app.query.conversation import save_conversation

        conv = Conversation(workspace_id=workspace_id, user_id=user.user_id)
        await save_conversation(redis, conv)
        cid = conv.id
        body.conversation_id = cid

    # One run per conversation. If a run is already active (e.g. a duplicate
    # submit), do NOT start a second generation — just tail the existing one.
    import uuid as _uuid

    run_id = _uuid.uuid4().hex
    started = await run_store.acquire_run(redis, cid, run_id)

    if started:
        # Producer owns its OWN redis+engine: the request's connections close when
        # the tailer ends, but generation must outlive the request.
        prod_redis = await _get_redis()
        prod_engine = await _get_engine()

        async def _producer_with_cleanup():
            try:
                await _run_producer(
                    redis=prod_redis, engine=prod_engine, body=body,
                    workspace_id=workspace_id, user_id=user.user_id,
                    team_id=user.team_id, sql_visible=sql_visible, cid=cid,
                )
            finally:
                await prod_redis.aclose()
                await prod_engine.dispose()

        task = asyncio.create_task(_producer_with_cleanup())
        _PRODUCERS.add(task)
        task.add_done_callback(_PRODUCERS.discard)

    async def event_generator():
        try:
            async for event in _tail_events(redis, cid, request):
                yield event
        finally:
            await redis.aclose()
            await engine.dispose()

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: Run the focused + full query suites**

Run: `pytest backend/tests/test_query_resume.py backend/tests/test_query.py -v`
Expected: PASS.

> The existing `test_query.py` fixture builds `mock_redis` as a bare `AsyncMock`, which does not implement `xadd`/`xread`. In this step, update that fixture's `_get_redis` patch to return `FakeRedis(decode_responses=True)` (mirroring `test_query_resume.py`) so the stream tailer works, then re-run. Keep the rate-limit int returns by calling `await fr.set(...)` is unnecessary — `check_rate_limit` uses `incr/expire/ttl` which FakeRedis implements natively.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/query.py backend/tests/test_query_resume.py backend/tests/test_query.py
git commit -m "feat(query): POST spawns durable producer, response tails the run stream"
```

---

## Task 6: `GET /api/query/{cid}/status` endpoint

**Files:**
- Modify: `backend/app/api/query.py` (add route near the other GET routes)
- Test: `backend/tests/test_query_resume.py`

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_query_resume.py
async def test_status_endpoint_reports_running_then_done(redis, auth_token, _JWKS_VALUE):
    from backend.app.main import app
    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=_JWKS_VALUE),
        patch.object(query_api, "_get_redis", AsyncMock(return_value=redis)),
    ):
        await run_store.acquire_run(redis, "cid-9", "run-x")
        client = TestClient(app)
        h = {"Authorization": f"Bearer {auth_token}"}
        r1 = client.get("/api/query/cid-9/status", headers=h)
        assert r1.status_code == 200 and r1.json()["status"] == "running"

        await run_store.finish_run(redis, "cid-9", "complete")
        r2 = client.get("/api/query/cid-9/status", headers=h)
        assert r2.json()["status"] == "complete"

        r3 = client.get("/api/query/unknown/status", headers=h)
        assert r3.json()["status"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_query_resume.py -k status_endpoint -v`
Expected: FAIL — 404 (route not defined).

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/api/query.py` (after the `GET /conversations/{id}` route):

```python
@router.get("/query/{conversation_id}/status", summary="Run status for a conversation")
async def get_run_status(
    conversation_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict:
    """Return {"status": "running"|"complete"|"error"|null}.

    The frontend uses this on load to decide: resume the live stream
    (running) or just render persisted history (complete/null).
    """
    redis = await _get_redis()
    try:
        return {"status": await run_store.get_status(redis, conversation_id)}
    finally:
        await redis.aclose()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_query_resume.py -k status_endpoint -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/query.py backend/tests/test_query_resume.py
git commit -m "feat(query): GET /query/{cid}/status for resume decisioning"
```

---

## Task 7: `GET /api/query/{cid}/stream` resume endpoint

**Files:**
- Modify: `backend/app/api/query.py`
- Test: `backend/tests/test_query_resume.py`

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_query_resume.py
async def test_resume_stream_replays_buffered_events(redis, auth_token, _JWKS_VALUE):
    from backend.app.main import app
    # Pre-populate a run as if a producer had already written events.
    await run_store.acquire_run(redis, "cid-7", "run-7")
    await run_store.append_event(redis, "cid-7", {"event": "status", "data": '{"status":"thinking"}'})
    await run_store.append_event(redis, "cid-7", {"event": "sql", "data": '{"sql":"SELECT 1"}'})
    await run_store.append_event(redis, "cid-7", {"event": "done", "data": "{}"})
    await run_store.finish_run(redis, "cid-7", "complete")

    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=_JWKS_VALUE),
        patch.object(query_api, "_get_redis", AsyncMock(return_value=redis)),
    ):
        client = TestClient(app)
        with client.stream(
            "GET", "/api/query/cid-7/stream",
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            assert resp.status_code == 200
            body = b""
            for chunk in resp.iter_bytes():
                body += chunk
                if b"done" in body:
                    break
    assert b"thinking" in body and b"SELECT 1" in body and b"done" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_query_resume.py -k resume_stream -v`
Expected: FAIL — 404.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/api/query.py`:

```python
@router.get("/query/{conversation_id}/stream", summary="Resume/tail a run's SSE stream")
async def resume_query_stream(
    conversation_id: str,
    request: Request,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> EventSourceResponse:
    """Re-attach to an in-flight (or just-finished) run and replay its events.

    Used by the frontend after a page refresh: it replays everything from the
    start of the run, then live-tails until the terminal event.
    """
    redis = await _get_redis()

    async def event_generator():
        try:
            async for event in _tail_events(redis, conversation_id, request):
                yield event
        finally:
            await redis.aclose()

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_query_resume.py -v`
Expected: PASS (all resume tests green).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/query.py backend/tests/test_query_resume.py
git commit -m "feat(query): GET /query/{cid}/stream resume endpoint"
```

---

## Task 8: Frontend API client — status + resume stream

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add `getRunStatus`**

After `fetchConversation` (around line 226), add:

```typescript
/**
 * Get the run status for a conversation: "running" | "complete" | "error" | null.
 * Used on load to decide whether to resume the live stream or render history.
 */
export async function getRunStatus(
  conversationId: string,
  tokenOverride?: string,
): Promise<{ status: string | null }> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/query/${conversationId}/status`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) return { status: null };
  return res.json();
}
```

- [ ] **Step 2: Add `streamResume`**

Add a GET-based twin of `streamQuery` (reuses the same `ReadableStream` pump shape):

```typescript
/**
 * Re-attach to an in-flight run's SSE stream (GET). Mirrors streamQuery's
 * reader/abort contract so the same SSE-consume loop can drive it.
 */
export function streamResume(
  conversationId: string,
  token: string = "",
): { reader: ReadableStreamDefaultReader<Uint8Array>; abort: () => void } {
  const controller = new AbortController();
  const responsePromise = fetch(`${API_BASE}/api/query/${conversationId}/stream`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
    signal: controller.signal,
    credentials: "omit",
  });

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await responsePromise;
        if (!response.ok || !response.body) {
          controller.error(new Error(`HTTP ${response.status}`));
          return;
        }
        const reader = response.body.getReader();
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            controller.close();
            break;
          }
          controller.enqueue(value);
        }
      } catch (err) {
        controller.error(err);
      }
    },
  });

  return { reader: stream.getReader(), abort: () => controller.abort() };
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors in `lib/api.ts`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(web): API client for run status + resume stream"
```

---

## Task 9: Frontend — extract reusable SSE consumer

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`

This refactor pulls the inline SSE-consume loop (lines ~317-450) into a function so both the live `POST` path and the new resume path share it. Behavior is unchanged for the live path.

- [ ] **Step 1: Add the consumer function**

Inside the `ChatPage` component (so it can call the `setMessages`/`setError`/etc. setters and `router`), define a `useCallback` BEFORE `handleSubmit`:

```typescript
// Consume an SSE reader, applying events to the assistant message `targetId`.
// Shared by the live POST path and the resume-on-load path.
const consumeStream = useCallback(
  async (
    reader: ReadableStreamDefaultReader<Uint8Array>,
    targetId: string,
  ): Promise<void> => {
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = parseSSEChunk(buffer);
      const lastNewline = buffer.lastIndexOf("\n\n");
      if (lastNewline >= 0) buffer = buffer.slice(lastNewline + 2);

      for (const { event, data } of events) {
        try {
          const payload = JSON.parse(data);
          switch (event) {
            case "status": {
              const statusMsg = payload.message || "";
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === targetId
                    ? {
                        ...m,
                        content: m.content ? `${m.content}\n${statusMsg}` : statusMsg,
                        status: payload.status === "complete" ? "complete" : "streaming",
                      }
                    : m,
                ),
              );
              if (payload.conversation_id) setConversationId(payload.conversation_id);
              break;
            }
            case "sql": {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === targetId
                    ? { ...m, sql: payload.sql, content: payload.explanation || m.content }
                    : m,
                ),
              );
              break;
            }
            case "chart": {
              const cfg = payload.chart_config || payload.chart_spec || {};
              const spec: ChartSpec = {
                type: cfg.type || payload.chart_type || "bar",
                title: cfg.title,
                xKey: cfg.xKey,
                yKeys: cfg.yKeys,
                colors: cfg.colors,
                data: payload.chart_data || cfg.data || [],
                chart_url: payload.chart_url,
                csv_url: payload.csv_url,
                row_count: payload.row_count,
              };
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === targetId ? { ...m, chartSpec: spec, chartUrl: payload.chart_url } : m,
                ),
              );
              setActiveArtifactMsgId(targetId);
              break;
            }
            case "insight": {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === targetId
                    ? { ...m, summary: payload.summary, suggestions: payload.suggestions }
                    : m,
                ),
              );
              break;
            }
            case "error": {
              setError(payload.error);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === targetId ? { ...m, status: "error", error: payload.error } : m,
                ),
              );
              break;
            }
            case "done": {
              if (payload.conversation_id) {
                setConversationId(payload.conversation_id);
                router.replace(`/chat?cid=${payload.conversation_id}`, { scroll: false });
              }
              setMessages((prev) =>
                prev.map((m) => (m.id === targetId ? { ...m, status: "complete" } : m)),
              );
              break;
            }
          }
        } catch {
          // Malformed event data — skip
        }
      }
    }
  },
  [router],
);
```

- [ ] **Step 2: Use it in `handleSubmit`**

Replace the inline `while (true) { ... }` loop in `handleSubmit` (lines ~320-450) with:

```typescript
        const { reader, abort } = streamQuery(q, conversationId || undefined, workspaceId, token);
        abortRef.current = abort;
        await consumeStream(reader, assistantMsg.id);
        setIsStreaming(false);
```

Keep the existing surrounding `try/catch/finally` (the abort + error handling at lines ~451-473) intact.

- [ ] **Step 3: Type-check + lint**

Run: `cd frontend && npx tsc --noEmit && npx eslint src/app/chat/page.tsx`
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/chat/page.tsx
git commit -m "refactor(web): extract reusable consumeStream from live SSE loop"
```

---

## Task 10: Frontend — resume on load when run is active

**Files:**
- Modify: `frontend/src/app/chat/page.tsx` (the load effect at lines ~207-243)
- Import: add `getRunStatus, streamResume` to the existing `@/lib/api` import (line 5)

- [ ] **Step 1: Add resume logic to the load effect**

After `setMessages(formattedMessages);` and the chart-panel block inside the `fetchConversation(...).then(...)` (around line 235), check run status and resume if active:

```typescript
            // If a run is still generating server-side (e.g. user refreshed
            // mid-answer), re-attach to its live stream and finish the turn.
            const last = formattedMessages[formattedMessages.length - 1];
            const danglingUser = last && last.role === "user";
            getRunStatus(conversationId, token).then(({ status }) => {
              if (status !== "running" || !danglingUser) return;
              const assistantId = `resume-${conversationId}-${Date.now()}`;
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "", status: "streaming", id: assistantId },
              ]);
              setIsStreaming(true);
              const { reader, abort } = streamResume(conversationId, token);
              abortRef.current = abort;
              consumeStream(reader, assistantId)
                .catch(() => {})
                .finally(() => {
                  abortRef.current = null;
                  setIsStreaming(false);
                });
            });
```

> The assistant-message object literal must match the shape `setMessages` uses elsewhere — mirror the `assistantMsg` literal built in `handleSubmit` (around lines 296-302), adding any required fields (e.g. `sql: null`, `chartSpec: null`) if the TS type demands them.

- [ ] **Step 2: Update the import**

Line 5 becomes:

```typescript
import { streamQuery, streamResume, getRunStatus, fetchConversations, fetchConversation, deleteConversation, fetchWorkspaceSuggestions } from "@/lib/api";
```

- [ ] **Step 3: Type-check + lint**

Run: `cd frontend && npx tsc --noEmit && npx eslint src/app/chat/page.tsx`
Expected: no new errors.

- [ ] **Step 4: Frontend build check**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/chat/page.tsx
git commit -m "feat(web): resume in-flight answer on chat reload"
```

---

## Task 11: Verify the slice end-to-end (smoke)

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite**

Run: `pytest backend/tests -q`
Expected: all pass (full suite once before the gate, per project test cadence).

- [ ] **Step 2: Boot + login smoke**

Run: `bash smoke/check.sh`
Expected: boot + Keycloak login round-trip OK.

- [ ] **Step 3: Manual resume verification (browser, per CLAUDE.md visual-verify)**

1. Start the dev stack; open `aria.localhost/chat`.
2. Ask "Show monthly revenue by region".
3. While generation is in progress, hit F5.
4. Expected: after reload the page replays the in-flight turn and it completes
   live (SQL + chart appear) — instead of an empty assistant bubble.
5. Capture a screenshot as run-evidence.

- [ ] **Step 4: Run done-check**

Run: `bash smoke/done-check.sh`
Expected: BE tests + FE tests + API-has-UI-surface + boot/login smoke all green.

- [ ] **Step 5: Commit any fixes**

```bash
git add -A && git commit -m "test: smoke + done-check for resumable streaming slice"
```

---

## Self-Review Notes (author)

- **Spec coverage:** run_store (Tasks 2-3) ✔; detached producer + tailer (Tasks 4-5) ✔; status endpoint (Task 6) ✔; resume endpoint (Task 7) ✔; one-run-per-cid lock (Task 2, used in Task 5) ✔; no-dup user message — handled by creating an *empty* conversation in the endpoint and letting the unchanged pipeline append the user message once (Task 5) ✔; SQL-visibility preserved by driving the already-gated `process_query` wrapper in the producer (Task 4) ✔; frontend resume vertical slice (Tasks 8-10) ✔; smoke/visual-verify (Task 11) ✔.
- **Deferred to Plan 2 (Prefect deploy-durability):** heartbeat/staleness, fencing-token reclaim, `reconcile_stalled_runs` flow, `process_query` `resume` flag (only needed when reconcile *re-runs* a pipeline), prod `docker-compose` Prefect worker. None are required for client-refresh survival, which is the reported bug.
- **Naming consistency:** `acquire_run`, `append_event`, `read_events`, `finish_run`, `get_status`, `_run_producer`, `_tail_events`, `getRunStatus`, `streamResume`, `consumeStream` used identically across tasks.
- **Risk watch:** `_PRODUCERS` set prevents GC of detached tasks; producer uses its own redis/engine so it outlives the request's connections.
