# Massive-Export Phase 3 — Batched Streaming Export + Async Prefect Delivery

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the in-memory, RAM-loading export worker (which delivers an unreachable internal URL via a `ValueError` that the chat UI renders as a red "Query execution failed") with a durable `export_jobs` record + a batched, streaming, memory-bounded Prefect export flow, dispatched from chat with a clean `export` SSE event instead of an error.

**Architecture:** Routing in `pipeline._execute_sql` already decides the export band (Phase 2). Phase 3 changes what the export band *does*: instead of running the synchronous `export_massive_query_to_minio` worker and raising `ValueError`, it (1) inserts an `export_jobs` row (`queued`), (2) dispatches an async export flow, and (3) raises a typed `ExportDispatched` signal that `process_query` catches **before** its generic self-correction handler and turns into an `export` SSE event. The export flow streams the DB result in batches (`stream_query`), writes a streaming CSV straight to MinIO multipart (`ArtifactStore.upload_csv_stream`), truncates at `max_export_row_limit`, mints a presigned URL, and advances the job to `success`/`error`. The flow core is pure async (unit-tested without Prefect), mirroring `app/flows/reconcile.py`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, Prefect (lazy-imported), MinIO SDK (`put_object` multipart), pytest + `unittest.mock`. Per-dialect drivers: `oracledb`, `psycopg2`, `pymysql`, `pymssql`.

**Scope note (phase boundary):** Phase 3 is **backend only** — it makes chat produce durable, streamed export jobs. The read API (`GET /api/exports`, `GET /api/exports/{id}`, download proxy) and the FE Exports page + inline download button are **Phase 4** (spec §D delivery surfaces). After Phase 3, an export job is observable via the DB and the `export` SSE event carries `export_job_id`; the clickable, browser-reachable link is finalized in Phase 4. This is a deliberate, testable boundary: the flow end-to-end is verified with mocked DB stream + mocked MinIO, and the `export_jobs` lifecycle is asserted directly.

**Spec:** `docs/superpowers/specs/2026-06-30-massive-query-export-redesign-design.md` §C (batched streaming export) + §D (status tracking; the durable `export_jobs` record and the dispatch half — the API/FE half is Phase 4).

---

## File Structure

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `backend/app/models/export_job.py` | **Create** | `ExportJob` ORM model + `ExportStatus` enum on `export_jobs`. |
| `backend/app/models/__init__.py` | Modify | Side-effect import of `export_job` so the table registers on `Base.metadata`. |
| `backend/alembic/versions/<rev>_add_export_jobs_table.py` | **Create** | Alembic migration creating `export_jobs` (down_revision = `03a3c29156e0`). |
| `backend/app/db/executor.py` | Modify | Add `stream_query(sql, config, batch_size) -> Iterator[list[dict]]` per dialect + a `stream_query_sync` public function. |
| `agents/artifact_store.py` | Modify | Add `ArtifactStore.upload_csv_stream(rows_iter, *, key, ...)` — lazy CSV-bytes generator → MinIO multipart `put_object(length=-1, part_size=...)`. |
| `backend/app/flows/export.py` | **Create** | `export_query_core(...)` pure-async flow body + `get_export_flow()` Prefect wrapper (mirrors `reconcile.py`). |
| `backend/app/query/export_dispatch.py` | **Create** | `ExportDispatched` exception + `create_export_job(...)` + `dispatch_export_job(...)` (run_deployment in prod, asyncio background fallback in dev). |
| `backend/app/query/pipeline.py` | Modify | `_offload_to_export`: replace inline-worker + `ValueError` with job-create + dispatch + `raise ExportDispatched`. `process_query`: catch `ExportDispatched` → emit `export` SSE event (both `_execute_sql` call sites). |
| `backend/tests/test_export_jobs_model.py` | **Create** | `export_jobs` lifecycle (queued → success/error) against an in-memory/SQLite-or-pg session. |
| `backend/tests/test_stream_query.py` | **Create** | Per-dialect `stream_query` batching via mocked cursor `fetchmany`. |
| `backend/tests/test_upload_csv_stream.py` | **Create** | Streaming CSV header/rows/coercion + MinIO `put_object` multipart call shape. |
| `backend/tests/test_export_flow.py` | **Create** | `export_query_core` end-to-end with mocked stream + mocked store: success, truncation, error → job state. |
| `backend/tests/test_export_dispatch.py` | **Create** | `create_export_job` inserts queued row; `ExportDispatched` carries id/estimate. |
| `backend/tests/test_massive_export.py` | Modify | Replace the 3 worker-contract tests + adapt the routing tests: export band now raises `ExportDispatched` (not `ValueError`) and creates a job. |
| `backend/tests/test_pipeline_export_event.py` | **Create** | `process_query` turns `ExportDispatched` into an `export` SSE event and does NOT self-correct. |

---

## Conventions to follow (read before coding)

- **Dialect routing** uses `config.db_type` (a `DatabaseType` StrEnum: `postgresql`/`mysql`/`oracle`/`mssql`) — see `backend/app/db/executor.py:336` `_EXECUTORS`.
- **Sync DB work runs in a thread pool** via `loop.run_in_executor(None, ...)` — see `execute_query` at `executor.py:428` and the worker at `backend/app/worker/tasks.py:33`.
- **Prefect is lazy-imported** inside `get_*_flow()`, never at module top, so unit tests need no Prefect server — see `reconcile.py:130-138`.
- **ORM models** use `Base, UUIDMixin, TimestampMixin` from `backend/app/models/base.py`; columns use `Mapped[...] = mapped_column(...)` with `server_default` for non-null backfills — see `backend/app/models/database.py:56-73`.
- **Alembic** revisions set `down_revision` to the current head (`03a3c29156e0`) and are hand-written (no autogenerate) — see `backend/alembic/versions/03a3c29156e0_*.py`.
- **MinIO upload** goes through `self.client.put_object(bucket_name, object_name, data, length, content_type)` — see `artifact_store.py:444`. For streaming, `length=-1` + `part_size` triggers multipart.
- **SSE events** are dicts `{"event": <name>, "data": json.dumps({...})}` yielded from `process_query` — see `pipeline.py:2299` (error) and `:2031` (done).
- **GateGuard**: present the 4 facts before the first Bash call each session, then retry. `SKIP_TDD_GUARD=1` only for non-logic changes (migration/model-only), with justification.
- **Tests run** from `backend/`: `cd backend && uv run pytest tests/ -q`. After editing pipeline/flow code that the running container loads, `docker restart aria-backend`.
- **DB-backed tests must create ONLY the table(s) under test, NOT the full registry.** `Base.metadata.create_all` sweeps in `Customer.settings` (JSONB) and other Postgres-only types that **fail to compile on SQLite** (`CompileError: can't render element of type JSONB`). `export_jobs` is FK-free, so create just it: `await conn.run_sync(ExportJob.__table__.create)`. (Discovered live in T1 — the first repo test to call full `create_all` on SQLite.)

---

## Task 1: `ExportJob` model + `export_jobs` migration

**Files:**
- Create: `backend/app/models/export_job.py`
- Modify: `backend/app/models/__init__.py:12-21` (add `export_job` to the side-effect import tuple)
- Create: `backend/alembic/versions/<rev>_add_export_jobs_table.py`
- Test: `backend/tests/test_export_jobs_model.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_export_jobs_model.py
"""export_jobs ORM model — columns, defaults, and status lifecycle."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.models import Base
from backend.app.models.export_job import ExportJob, ExportStatus


@pytest.mark.asyncio
async def test_export_job_defaults_to_queued_and_persists():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table (full create_all breaks on SQLite — JSONB)

    job_id = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        job = ExportJob(
            id=job_id,
            workspace_id="ws1",
            user_id="u1",
            conversation_id="ws1_u1",
            question="show all orders",
            sql="SELECT * FROM orders",
            total_estimate=5_000_000,
        )
        sess.add(job)
        await sess.commit()

    async with AsyncSession(engine) as sess:
        loaded = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        assert loaded is not None
        assert loaded.status == ExportStatus.QUEUED
        assert loaded.row_count is None
        assert loaded.truncated is False
        assert loaded.download_url is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_export_job_advances_to_success_with_url():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table (full create_all breaks on SQLite — JSONB)

    job_id = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        sess.add(
            ExportJob(
                id=job_id, workspace_id="ws1", user_id="u1",
                conversation_id="c", question="q", sql="SELECT 1",
            )
        )
        await sess.commit()
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        job.status = ExportStatus.SUCCESS
        job.row_count = 100_000
        job.truncated = True
        job.minio_key = "exports/ws1/c/data_export_abc.csv"
        job.download_url = "http://minio:9000/aria-artifacts/exports/ws1/c/data_export_abc.csv"
        await sess.commit()
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        assert job.status == ExportStatus.SUCCESS
        assert job.row_count == 100_000
        assert job.truncated is True
        assert "data_export_abc.csv" in job.download_url
    await engine.dispose()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_export_jobs_model.py -q`
Expected: FAIL with `ModuleNotFoundError: backend.app.models.export_job` (model not created yet). If it instead fails with a missing `aiosqlite` driver, see Risks — switch to the project's async test-DB fixture.

- [ ] **Step 3: Create the model**

```python
# backend/app/models/export_job.py
"""Durable record of a massive-query CSV export (Phase 3).

One row per export request dispatched from the chat pipeline. The async export
flow (``app/flows/export.py``) advances it queued → running → success/error and
records the streamed row count, truncation flag, MinIO key, and download URL.
Workspace-scoped; honors the same RBAC/SQL-visibility invariants as the query
that produced it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class ExportStatus(StrEnum):
    """Lifecycle states for an export job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ExportJob(Base, UUIDMixin, TimestampMixin):
    """A queued/running/finished massive-query CSV export."""

    __tablename__ = "export_jobs"

    # Scope / provenance (string identifiers, matching the pipeline's runtime ids;
    # NOT FKs — workspace_id is a customer slug, user_id may be a Keycloak sub).
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    status: Mapped[ExportStatus] = mapped_column(
        String(16), nullable=False, default=ExportStatus.QUEUED, server_default="queued", index=True
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    total_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Result
    minio_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefect_flow_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps (created_at/updated_at come from TimestampMixin)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ExportJob {self.id} [{self.status}] rows={self.row_count}>"
```

NOTE: `status` is stored as `String(16)` (not a PG enum) to keep the migration simple and avoid a second `database_type`-style enum type; the `ExportStatus` StrEnum maps cleanly because its values are the stored strings.

- [ ] **Step 4: Register the table on `Base.metadata`**

In `backend/app/models/__init__.py`, add `export_job` to the side-effect import tuple (it sits between `enums` and `governance`):

```python
from . import (  # noqa: F401  (imported for metadata registration, not direct use)
    artifact,
    database,
    enums,
    export_job,
    governance,
    organization,
    query,
    token,
)
```

- [ ] **Step 5: Run the model test to verify it passes**

Run: `cd backend && uv run pytest tests/test_export_jobs_model.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Generate the migration manually (mirror Phase 1's hand-written style)**

First pick a fresh 12-hex revision id and confirm uniqueness: `ls backend/alembic/versions/`. Create `backend/alembic/versions/a1b2c3d4e5f6_add_export_jobs_table.py` (replace `a1b2c3d4e5f6` with your chosen id, and use it consistently below):

```python
"""add export_jobs table

Revision ID: a1b2c3d4e5f6
Revises: 03a3c29156e0
Create Date: 2026-07-01

Durable record for batched-streaming CSV exports dispatched from chat (Phase 3).
One row per export, advanced queued → running → success/error by the Prefect
export flow.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "03a3c29156e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("conversation_id", sa.String(255), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("sql", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_estimate", sa.Integer(), nullable=True),
        sa.Column("minio_key", sa.String(1024), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("prefect_flow_run_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # UUIDMixin.id sets index=True → the model declares ix_export_jobs_id; create it
    # too (every other UUIDMixin table does) so model and migration don't drift.
    op.create_index("ix_export_jobs_id", "export_jobs", ["id"])
    op.create_index("ix_export_jobs_workspace_id", "export_jobs", ["workspace_id"])
    op.create_index("ix_export_jobs_conversation_id", "export_jobs", ["conversation_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_conversation_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_workspace_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_id", table_name="export_jobs")
    op.drop_table("export_jobs")
```

- [ ] **Step 7: Apply the migration and verify head**

Run: `cd backend && uv run alembic upgrade head && uv run alembic current`
Expected: `current` shows the new revision id `(head)`. If the metadata DB lives in the container, run alembic inside `aria-backend` (see `docs/engineering-notes.md`); otherwise apply against the local DB the tests use.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/export_job.py backend/app/models/__init__.py backend/alembic/versions/a1b2c3d4e5f6_add_export_jobs_table.py backend/tests/test_export_jobs_model.py
git commit -m "feat(backend): add export_jobs model + migration (massive-export Phase 3 T1)"
```
(This commit carries a test, so the TDD pre-commit guard passes without `SKIP_TDD_GUARD`.)

---

## Task 2: `stream_query` executors (batched, memory-bounded reads)

**Files:**
- Modify: `backend/app/db/executor.py` (add `stream_query` to base + each executor + `stream_query_sync` public fn)
- Test: `backend/tests/test_stream_query.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_stream_query.py
"""stream_query yields the DB result in batches via fetchmany, per dialect."""

from __future__ import annotations

import psycopg2.extras  # noqa: F401 — prime the submodule so patch("psycopg2.extras") resolves
from unittest.mock import MagicMock, patch

from backend.app.db.models import DatabaseType, DBConfig


def _cfg(db_type: DatabaseType) -> DBConfig:
    return DBConfig(
        db_type=db_type, host="h", port=0, database="d",
        username="u", password="p", export_batch_size=2,
    )


def _fake_cursor(rows, description):
    """A cursor whose fetchmany(n) drains `rows` in chunks of n."""
    cur = MagicMock()
    cur.description = description
    state = {"i": 0}

    def _fetchmany(n):
        i = state["i"]
        chunk = rows[i : i + n]
        state["i"] = i + n
        return chunk

    cur.fetchmany.side_effect = _fetchmany
    return cur


def test_postgres_stream_query_batches_rows():
    from backend.app.db import executor

    # psycopg2 RealDictCursor yields dict rows directly.
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    cur = _fake_cursor(rows, description=[("id",)])
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    with patch("psycopg2.connect", return_value=conn), patch("psycopg2.extras"):
        ex = executor.PostgreSQLExecutor(_cfg(DatabaseType.POSTGRESQL))
        batches = list(ex.stream_query("SELECT * FROM t", batch_size=2))
    assert [len(b) for b in batches] == [2, 1]
    assert batches[0] == [{"id": 1}, {"id": 2}]
    assert batches[1] == [{"id": 3}]


def test_oracle_stream_query_zips_columns_and_batches():
    from backend.app.db import executor

    # oracledb returns tuples; the executor must zip with cur.description names.
    rows = [(1, "a"), (2, "b"), (3, "c")]
    cur = _fake_cursor(rows, description=[("ID",), ("NAME",)])
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    fake_oracledb = MagicMock()
    fake_oracledb.connect.return_value = conn
    with patch.dict("sys.modules", {"oracledb": fake_oracledb}):
        ex = executor.OracleExecutor(_cfg(DatabaseType.ORACLE))
        batches = list(ex.stream_query("SELECT id, name FROM t", batch_size=2))
    assert [len(b) for b in batches] == [2, 1]
    assert batches[0] == [{"ID": 1, "NAME": "a"}, {"ID": 2, "NAME": "b"}]
    assert batches[1] == [{"ID": 3, "NAME": "c"}]
    # arraysize set to the batch size for round-trip efficiency.
    assert cur.arraysize == 2


def test_stream_query_sync_dispatches_to_executor():
    from backend.app.db import executor

    cfg = _cfg(DatabaseType.POSTGRESQL)
    sentinel = iter([[{"id": 1}]])
    with patch.object(executor.PostgreSQLExecutor, "stream_query", return_value=sentinel) as m:
        gen = executor.stream_query_sync("SELECT 1", cfg, batch_size=500)
        assert list(gen) == [[{"id": 1}]]
    m.assert_called_once()
```

NOTE on the Oracle test: `OracleExecutor.execute` calls `get_settings()` for thick-mode; the `stream_query` body below guards that the same way. The test patches `sys.modules["oracledb"]`; if `get_settings().oracle_client_lib_dir` is set in the test env, `_init_oracle_thick_mode` runs against the fake — keep `oracle_client_lib_dir` unset in tests (it is, by default).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_stream_query.py -q`
Expected: FAIL with `AttributeError: ... has no attribute 'stream_query'`.

- [ ] **Step 3: Add `stream_query` to the base + each executor and the public fn**

In `backend/app/db/executor.py`, add to the top imports (next to `from typing import Any`):

```python
from collections.abc import Iterator
```

Add to `DatabaseExecutor` (base, after `explain` at line ~116):

```python
    def stream_query(
        self, sql: str, params: dict[str, Any] | None = None, *, batch_size: int = 50_000
    ) -> Iterator[list[dict[str, Any]]]:
        """Yield rows in batches of ``batch_size`` without buffering the whole result."""
        raise NotImplementedError
```

Add to `PostgreSQLExecutor` (server-side named cursor so the client does not buffer):

```python
    def stream_query(
        self, sql: str, params: dict[str, Any] | None = None, *, batch_size: int = 50_000
    ) -> Iterator[list[dict[str, Any]]]:
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
            # Named cursor → server-side; itersize controls network fetch batching.
            with conn.cursor(name="aria_export", cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.itersize = batch_size
                cur.execute(sql, params or {})
                while True:
                    chunk = cur.fetchmany(batch_size)
                    if not chunk:
                        break
                    yield [dict(row) for row in chunk]
        finally:
            conn.close()
```

Add to `MySQLExecutor` (unbuffered `SSDictCursor`):

```python
    def stream_query(
        self, sql: str, params: dict[str, Any] | None = None, *, batch_size: int = 50_000
    ) -> Iterator[list[dict[str, Any]]]:
        import pymysql
        import pymysql.cursors

        conn = pymysql.connect(
            host=self.config.host,
            port=self.config.get_port(),
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            cursorclass=pymysql.cursors.SSDictCursor,  # unbuffered, dict rows
            **(self.config.options or {}),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or {})
                while True:
                    chunk = cur.fetchmany(batch_size)
                    if not chunk:
                        break
                    yield list(chunk)
        finally:
            conn.close()
```

Add to `OracleExecutor` (`arraysize` + `fetchmany`; zip tuple rows with column names):

```python
    def stream_query(
        self, sql: str, params: dict[str, Any] | None = None, *, batch_size: int = 50_000
    ) -> Iterator[list[dict[str, Any]]]:
        import oracledb

        from backend.app.core.config import get_settings

        settings = get_settings()
        if settings.oracle_client_lib_dir:
            _init_oracle_thick_mode()

        dsn = f"{self.config.host}:{self.config.get_port()}/{self.config.database}"
        conn = oracledb.connect(user=self.config.username, password=self.config.password, dsn=dsn)
        try:
            with conn.cursor() as cur:
                cur.arraysize = batch_size  # round-trip efficiency
                cur.execute(sql, params or {})
                columns = [d[0] for d in cur.description] if cur.description else []
                while True:
                    chunk = cur.fetchmany(batch_size)
                    if not chunk:
                        break
                    yield [dict(zip(columns, row, strict=False)) for row in chunk]
        finally:
            conn.close()
```

Add to `MSSQLExecutor` (`fetchmany`; `as_dict=True` already yields dict rows):

```python
    def stream_query(
        self, sql: str, params: dict[str, Any] | None = None, *, batch_size: int = 50_000
    ) -> Iterator[list[dict[str, Any]]]:
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
                while True:
                    chunk = cur.fetchmany(batch_size)
                    if not chunk:
                        break
                    yield list(chunk)
        finally:
            conn.close()
```

Add the public dispatcher near `execute_query_sync` (after line ~425):

```python
def stream_query_sync(
    sql: str,
    config: DBConfig,
    *,
    batch_size: int = 50_000,
    params: dict[str, Any] | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """Stream a SQL query's rows in batches (memory-bounded). Synchronous; run in a
    thread pool from async callers — see app/flows/export.py."""
    executor = get_executor(config)
    return executor.stream_query(sql, params, batch_size=batch_size)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_stream_query.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/executor.py backend/tests/test_stream_query.py
git commit -m "feat(backend): add per-dialect stream_query (batched, memory-bounded) — Phase 3 T2"
```

---

## Task 3: `ArtifactStore.upload_csv_stream` (streaming CSV → MinIO multipart)

**Files:**
- Modify: `agents/artifact_store.py` (add `_IteratorIO` adapter + `_MULTIPART_PART_SIZE` const + `upload_csv_stream` method)
- Test: `backend/tests/test_upload_csv_stream.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_upload_csv_stream.py
"""upload_csv_stream lazily turns a batch iterator into a CSV byte stream and
hands it to MinIO put_object as a multipart (length=-1) upload."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from agents.artifact_store import ArtifactStore


def _store_with_fake_client():
    store = ArtifactStore(endpoint="minio:9000", bucket="aria-artifacts")
    client = MagicMock()
    client.put_object.return_value = MagicMock(etag="deadbeef")
    store._client = client  # bypass connect()
    return store, client


def test_upload_csv_stream_writes_header_rows_and_coerces_values():
    store, client = _store_with_fake_client()
    batches = [
        [{"id": 1, "amt": Decimal("10.5"), "ts": datetime(2026, 7, 1), "note": None}],
        [{"id": 2, "amt": Decimal("20"), "ts": datetime(2026, 7, 2), "note": "x"}],
    ]
    ref = store.upload_csv_stream(iter(batches), key="exports/ws1/c/data.csv")

    # MinIO multipart: length=-1 + a part_size kwarg.
    _, kwargs = client.put_object.call_args
    assert kwargs["length"] == -1
    assert kwargs["part_size"] >= 5 * 1024 * 1024
    assert kwargs["object_name"] == "exports/ws1/c/data.csv"

    # Drain the stream object that was handed to put_object and parse it back.
    stream = kwargs["data"]
    raw = stream.read()
    text = raw.decode("utf-8")
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert parsed[0] == {"id": "1", "amt": "10.5", "ts": "2026-07-01 00:00:00", "note": ""}
    assert parsed[1]["note"] == "x"
    assert ref.format == "csv"
    assert ref.key == "exports/ws1/c/data.csv"


def test_upload_csv_stream_empty_yields_no_upload():
    store, client = _store_with_fake_client()
    ref = store.upload_csv_stream(iter([]), key="exports/ws1/c/empty.csv")
    assert ref is None
    client.put_object.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_upload_csv_stream.py -q`
Expected: FAIL with `AttributeError: 'ArtifactStore' object has no attribute 'upload_csv_stream'`.

- [ ] **Step 3: Implement `_IteratorIO`, the part-size const, and `upload_csv_stream`**

In `agents/artifact_store.py`, add `Iterator` to the typing imports near the top:

```python
from collections.abc import Iterator
```

Add the part-size constant after `_CONTENT_TYPES` (~line 126):

```python
_MULTIPART_PART_SIZE = 10 * 1024 * 1024  # 10 MiB MinIO multipart part
```

Add the `_IteratorIO` adapter at module level, right after the `ArtifactRef` dataclass (before `_CONTENT_TYPES` or before `class ArtifactStore` — anywhere at module scope works):

```python
class _IteratorIO(io.RawIOBase):
    """Adapt an iterator of byte chunks into a read()-able binary stream so the
    MinIO SDK can pull from it for a multipart upload without materializing the
    whole CSV. Tracks total bytes for the ArtifactRef size."""

    def __init__(self, chunks: Iterator[bytes]) -> None:
        self._chunks = chunks
        self._leftover = b""
        self.bytes_read = 0

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:  # type: ignore[override]
        if not self._leftover:
            try:
                self._leftover = next(self._chunks)
            except StopIteration:
                return 0
        n = min(len(b), len(self._leftover))
        b[:n] = self._leftover[:n]
        self._leftover = self._leftover[n:]
        self.bytes_read += n
        return n
```

Add the method to `ArtifactStore` (after `upload_csv`, ~line 290):

```python
    def upload_csv_stream(
        self,
        batches: Iterator[list[dict[str, object]]],
        *,
        key: str,
        content_type: str = "text/csv; charset=utf-8",
    ) -> ArtifactRef | None:
        """Stream batches of dict rows to MinIO as a single CSV, multipart.

        Neither the full result set nor the full CSV is held in memory: a lazy
        generator yields CSV byte chunks (header from the first row's keys, then
        rows with safe per-cell coercion), wrapped in a read()-able stream and
        uploaded via ``put_object(length=-1, part_size=...)`` (MinIO multipart).

        Returns None (no upload) if the iterator yields no rows.
        """
        import itertools

        # Peek the first non-empty batch to derive the header. If there are no
        # rows at all, skip the upload entirely.
        first_batch: list[dict[str, object]] | None = None
        for b in batches:
            if b:
                first_batch = b
                break
        if first_batch is None:
            log.info("artifact_store.csv_stream_empty", key=key)
            return None

        fieldnames = list(first_batch[0].keys())

        def _safe(v: object) -> str:
            return "" if v is None else str(v)

        def _byte_chunks() -> Iterator[bytes]:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            for batch in itertools.chain([first_batch], batches):
                for row in batch:
                    writer.writerow({k: _safe(row.get(k)) for k in fieldnames})
                chunk = buf.getvalue().encode("utf-8")
                buf.seek(0)
                buf.truncate(0)
                if chunk:
                    yield chunk

        stream = _IteratorIO(_byte_chunks())
        result = self.client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=stream,
            length=-1,
            part_size=_MULTIPART_PART_SIZE,
            content_type=content_type,
        )
        log.info("artifact_store.csv_stream_uploaded", key=key, etag=result.etag)
        return ArtifactRef(
            key=key,
            bucket=self._bucket,
            format="csv",
            size_bytes=getattr(stream, "bytes_read", 0),
            content_type=content_type,
            created_at=datetime.now(UTC).isoformat(),
            etag=result.etag,
            _store=self,
        )
```

Add `import csv` to the top of `agents/artifact_store.py` (the module currently imports `io`, `os`, `uuid` — add `csv`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_upload_csv_stream.py -q`
Expected: PASS (2 passed). The `csv.DictReader` round-trip confirms header + coercion; the `length=-1`/`part_size` asserts confirm multipart.

- [ ] **Step 5: Commit**

```bash
git add agents/artifact_store.py backend/tests/test_upload_csv_stream.py
git commit -m "feat(backend): ArtifactStore.upload_csv_stream — streaming CSV → MinIO multipart (Phase 3 T3)"
```

---

## Task 4: `export_query_core` Prefect flow (truncation, job lifecycle)

**Files:**
- Create: `backend/app/flows/export.py`
- Test: `backend/tests/test_export_flow.py`

This flow is the heart of §C. It mirrors `reconcile.py`: a pure-async core (unit-tested, no Prefect) + a lazy `get_export_flow()` Prefect wrapper. The core opens the stream, truncates at `max_export_row_limit`, streams to MinIO, mints a presigned URL, and advances the `export_jobs` row. The core takes an injected `session_factory` so tests can hand it a SQLite engine.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_export_flow.py
"""export_query_core: streams a bounded export to MinIO and advances the job."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.models import DatabaseType, DBConfig
from backend.app.models.export_job import ExportJob, ExportStatus


def _cfg() -> DBConfig:
    return DBConfig(
        db_type=DatabaseType.POSTGRESQL, host="h", port=5432, database="d",
        username="u", password="p", max_export_row_limit=5, export_batch_size=2,
    )


async def _seed_job(engine) -> uuid.UUID:
    jid = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        sess.add(ExportJob(
            id=jid, workspace_id="ws1", user_id="u1", conversation_id="c",
            question="all rows", sql="SELECT * FROM big", total_estimate=1_000_000,
        ))
        await sess.commit()
    return jid


class _FakeRef:
    def __init__(self, key):
        self.key = key
    def public_url(self):
        return ""
    def presigned_url(self, expires=0):
        return "http://minio:9000/aria-artifacts/" + self.key


@pytest.mark.asyncio
async def test_flow_success_writes_capped_rows_and_marks_success(monkeypatch):
    from backend.app.flows import export as flowmod

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table (full create_all breaks on SQLite — JSONB)
    jid = await _seed_job(engine)

    # 6 rows from the DB but ceiling is 5 → expect truncated=True, row_count=5.
    def fake_stream(sql, cfg, *, batch_size, params=None):
        yield [{"id": 1}, {"id": 2}]
        yield [{"id": 3}, {"id": 4}]
        yield [{"id": 5}, {"id": 6}]
    monkeypatch.setattr(flowmod, "stream_query_sync", fake_stream)

    written = {}

    class FakeStore:
        def upload_csv_stream(self, batches, *, key, **kw):
            written["rows"] = [r for b in batches for r in b]
            written["key"] = key
            return _FakeRef(key)
    monkeypatch.setattr(flowmod, "ArtifactStore", FakeStore)

    await flowmod.export_query_core(
        job_id=jid, sql="SELECT * FROM big", config=_cfg(),
        workspace_id="ws1", conversation_id="c", user_id="u1",
        session_factory=lambda: AsyncSession(engine),
    )

    assert len(written["rows"]) == 5  # capped at max_export_row_limit
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == jid))
        assert job.status == ExportStatus.SUCCESS
        assert job.row_count == 5
        assert job.truncated is True
        assert job.download_url and "aria-artifacts" in job.download_url
        assert job.completed_at is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_flow_marks_error_when_stream_raises(monkeypatch):
    from backend.app.flows import export as flowmod

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table (full create_all breaks on SQLite — JSONB)
    jid = await _seed_job(engine)

    def boom(sql, cfg, *, batch_size, params=None):
        raise RuntimeError("db down")
        yield  # pragma: no cover
    monkeypatch.setattr(flowmod, "stream_query_sync", boom)

    await flowmod.export_query_core(
        job_id=jid, sql="SELECT * FROM big", config=_cfg(),
        workspace_id="ws1", conversation_id="c", user_id="u1",
        session_factory=lambda: AsyncSession(engine),
    )

    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == jid))
        assert job.status == ExportStatus.ERROR
        assert "db down" in (job.error or "")
        assert job.download_url is None
    await engine.dispose()
```

NOTE: the success test asserts `row_count == 5` even though `stream_query_sync` is fully drained inside `upload_csv_stream` (the fake store materializes it). Because `_capped_batches` wraps the iterator and the fake store drains the *capped* iterator, the side-effect `stats` dict is populated to 5. The error test relies on the stream raising when first iterated; `upload_csv_stream`'s header-peek loop pulls the first batch, so the `RuntimeError` surfaces inside the core's try and is recorded as `status=error`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_export_flow.py -q`
Expected: FAIL with `ModuleNotFoundError: backend.app.flows.export`.

- [ ] **Step 3: Implement the flow core + Prefect wrapper**

```python
# backend/app/flows/export.py
"""Batched, streaming CSV export flow (massive-export Phase 3, spec §C).

The chat pipeline routes a too-large result to the export band, inserts an
``export_jobs`` row (queued), and dispatches this flow. The flow streams the
bare SQL in batches (memory-bounded), writes the first ``max_export_row_limit``
rows to a single CSV in MinIO (multipart), and advances the job to
success/error — recording row count, truncation, MinIO key, and a presigned URL.

Mirrors ``reconcile.py``: the orchestration core is pure async (unit-tested with
mocked stream + mocked store + an injected session factory), and the Prefect
decoration is applied lazily so importing this module never needs a Prefect
server. Durability across backend restarts comes from running it as a Prefect
deployment in prod (the in-process asyncio fallback is dev-only).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

# Imported at module top so tests can monkeypatch flowmod.stream_query_sync /
# flowmod.ArtifactStore.
from agents.artifact_store import ArtifactStore

from backend.app.db.executor import stream_query_sync
from backend.app.db.models import DBConfig
from backend.app.models.base import utcnow
from backend.app.models.export_job import ExportJob, ExportStatus

logger = logging.getLogger(__name__)

_PRESIGN_EXPIRES = 86_400 * 3  # 3 days


def _capped_batches(
    batches: Iterator[list[dict[str, Any]]], ceiling: int
) -> tuple[Iterator[list[dict[str, Any]]], dict[str, Any]]:
    """Wrap a batch iterator so it yields at most ``ceiling`` rows. The returned
    ``stats`` dict is filled as a side effect: row_count + truncated."""
    stats: dict[str, Any] = {"row_count": 0, "truncated": False}

    def _gen() -> Iterator[list[dict[str, Any]]]:
        remaining = ceiling
        for batch in batches:
            if remaining <= 0:
                stats["truncated"] = True
                break
            if len(batch) > remaining:
                stats["truncated"] = True
                batch = batch[:remaining]
            remaining -= len(batch)
            stats["row_count"] += len(batch)
            yield batch

    return _gen(), stats


async def _set_job(
    session_factory: Callable[[], AsyncSession], job_id: uuid.UUID, **values: Any
) -> None:
    async with session_factory() as sess:
        await sess.execute(update(ExportJob).where(ExportJob.id == job_id).values(**values))
        await sess.commit()


async def export_query_core(
    *,
    job_id: uuid.UUID,
    sql: str,
    config: DBConfig,
    workspace_id: str,
    conversation_id: str | None,
    user_id: str | None,
    session_factory: Callable[[], AsyncSession],
) -> None:
    """Run one export job end-to-end, advancing the export_jobs row.

    Never raises: any failure is recorded as ``status=error`` on the job so the
    chat surface and the (Phase 4) Exports list can show a terminal state.
    """
    ceiling = config.max_export_row_limit
    batch_size = min(config.export_batch_size, ceiling)

    try:
        # RUNNING write is INSIDE the try so a DB hiccup here routes to the
        # error handler instead of leaving the job stuck at queued.
        await _set_job(session_factory, job_id, status=ExportStatus.RUNNING, started_at=utcnow())

        loop = asyncio.get_event_loop()
        raw_batches = await loop.run_in_executor(
            None, lambda: stream_query_sync(sql, config, batch_size=batch_size)
        )
        capped, stats = _capped_batches(raw_batches, ceiling)

        store = ArtifactStore()
        key = f"exports/{workspace_id}/{conversation_id or 'adhoc'}/data_export_{uuid.uuid4().hex[:8]}.csv"
        # The blocking MinIO multipart upload (which pulls the stream, which pulls
        # the DB cursor) runs in a thread so the event loop is not blocked.
        ref = await loop.run_in_executor(None, lambda: store.upload_csv_stream(capped, key=key))

        if ref is None:
            await _set_job(
                session_factory, job_id, status=ExportStatus.SUCCESS,
                row_count=0, truncated=False, completed_at=utcnow(),
            )
            return

        url = ref.public_url() or ref.presigned_url(expires=_PRESIGN_EXPIRES)
        await _set_job(
            session_factory, job_id,
            status=ExportStatus.SUCCESS,
            row_count=stats["row_count"],
            truncated=stats["truncated"],
            minio_key=ref.key,
            download_url=url,
            completed_at=utcnow(),
        )
        logger.info(
            "Export job %s succeeded: %d rows (truncated=%s)",
            job_id, stats["row_count"], stats["truncated"],
        )
    except Exception as exc:  # noqa: BLE001 — terminal error recorded on the job
        logger.exception("Export job %s failed", job_id)
        try:
            await _set_job(
                session_factory, job_id, status=ExportStatus.ERROR,
                error=str(exc)[:2000], completed_at=utcnow(),
            )
        except Exception:  # noqa: BLE001 — job-row write itself failed; original already logged
            logger.exception("Failed to record ERROR terminal state for export job %s", job_id)


async def export_query_flow(
    job_id: str,
    sql: str,
    db_config_json: dict,
    workspace_id: str,
    conversation_id: str | None,
    user_id: str | None,
    max_export_row_limit: int,
    export_batch_size: int,
) -> None:
    """Prefect entrypoint: rebuild DBConfig + a session factory, then run the core.

    Imported lazily by the dispatcher; Prefect-serializable args only (no live
    SQLAlchemy objects), so DBConfig arrives as a plain dict.
    """
    from backend.app.api.query import _get_engine
    from backend.app.db.models import DatabaseType

    engine = await _get_engine()
    config = DBConfig(
        db_type=DatabaseType(db_config_json["db_type"]),
        host=db_config_json["host"], port=db_config_json["port"],
        database=db_config_json["database"], username=db_config_json["username"],
        password=db_config_json["password"], options=db_config_json.get("options"),
        max_row_limit=db_config_json.get("max_row_limit", 1000),
        max_export_row_limit=max_export_row_limit, export_batch_size=export_batch_size,
    )
    try:
        await export_query_core(
            job_id=uuid.UUID(job_id), sql=sql, config=config,
            workspace_id=workspace_id, conversation_id=conversation_id, user_id=user_id,
            session_factory=lambda: AsyncSession(engine),
        )
    finally:
        await engine.dispose()


def get_export_flow():
    """Return the Prefect-decorated export flow (for deployment registration).

    Prefect is imported here, not at module top, so unit tests that exercise the
    core never need a Prefect install/server.
    """
    from prefect import flow

    return flow(name="export-query", log_prints=True)(export_query_flow)
```

NOTE: `_get_engine` is imported from `backend.app.api.query` — confirm that symbol exists (it is used the same way in `reconcile.py:116`). If its name differs, mirror exactly what `reconcile.py` imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_export_flow.py -q`
Expected: PASS (2 passed) — success path caps at 5 rows + `truncated=True`; stream error → `status=error`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/flows/export.py backend/tests/test_export_flow.py
git commit -m "feat(backend): streaming export_query Prefect flow + truncation + job lifecycle (Phase 3 T4)"
```

---

## Task 5: `ExportDispatched` signal + `create_export_job` / `dispatch_export_job`

**Files:**
- Create: `backend/app/query/export_dispatch.py`
- Test: `backend/tests/test_export_dispatch.py`

This isolates the two side effects the export band needs (insert a job, dispatch the flow) so `_execute_sql` stays focused and `process_query` has a typed signal to catch.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_export_dispatch.py
"""create_export_job inserts a queued row; ExportDispatched carries the id+estimate."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.models import Base
from backend.app.models.export_job import ExportJob, ExportStatus
from backend.app.query.export_dispatch import ExportDispatched, create_export_job


@pytest.mark.asyncio
async def test_create_export_job_inserts_queued_row():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table (full create_all breaks on SQLite — JSONB)
    async with AsyncSession(engine) as sess:
        job_id = await create_export_job(
            sess, workspace_id="ws1", user_id="u1", conversation_id="c",
            question="all rows", sql="SELECT * FROM big", total_estimate=5_000_000,
        )
        await sess.commit()
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        assert job.status == ExportStatus.QUEUED
        assert job.total_estimate == 5_000_000
        assert job.sql == "SELECT * FROM big"
    await engine.dispose()


def test_export_dispatched_carries_job_id_and_estimate():
    jid = uuid.uuid4()
    exc = ExportDispatched(job_id=jid, estimated_rows=5_000_000)
    assert exc.job_id == jid
    assert exc.estimated_rows == 5_000_000
    assert "5,000,000" in str(exc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_export_dispatch.py -q`
Expected: FAIL with `ModuleNotFoundError: backend.app.query.export_dispatch`.

- [ ] **Step 3: Implement the dispatch module**

```python
# backend/app/query/export_dispatch.py
"""Export-band side effects: a typed dispatch signal + job creation + flow dispatch.

Kept out of pipeline._execute_sql so the executor stays focused. The pipeline
generator (process_query) catches ExportDispatched and turns it into a clean
``export`` SSE event — replacing the old ValueError-as-delivery hack that the FE
rendered as a red "Query execution failed" and that triggered a duplicate export
via SQL self-correction.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import DBConfig
from backend.app.models.export_job import ExportJob

logger = logging.getLogger(__name__)

# Strong refs to in-flight dev-fallback export tasks so they aren't GC'd before
# completion (asyncio only holds weak refs to bare create_task results).
_PENDING_EXPORT_TASKS: set[asyncio.Task] = set()


class ExportDispatched(Exception):
    """Raised by the export band to signal that the result is being exported
    asynchronously. NOT an error: process_query catches it BEFORE its generic
    self-correction handler and emits an ``export`` SSE event."""

    def __init__(self, *, job_id: uuid.UUID, estimated_rows: int) -> None:
        self.job_id = job_id
        self.estimated_rows = estimated_rows
        super().__init__(
            f"Result (~{estimated_rows:,} rows) too large to display; export job {job_id} dispatched."
        )


async def create_export_job(
    db: AsyncSession,
    *,
    workspace_id: str,
    user_id: str | None,
    conversation_id: str | None,
    question: str | None,
    sql: str,
    total_estimate: int,
) -> uuid.UUID:
    """Insert a queued export_jobs row and return its id. Caller commits."""
    job = ExportJob(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        sql=sql,
        total_estimate=total_estimate,
    )
    db.add(job)
    await db.flush()  # assign + surface PK without forcing the caller's commit boundary
    return job.id


def _config_to_json(config: DBConfig) -> dict:
    return {
        "db_type": config.db_type.value,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "username": config.username,
        "password": config.password,
        "options": config.options,
        "max_row_limit": config.max_row_limit,
    }


async def dispatch_export_job(
    *,
    job_id: uuid.UUID,
    sql: str,
    config: DBConfig,
    workspace_id: str,
    conversation_id: str | None,
    user_id: str | None,
) -> None:
    """Schedule the export flow. Prefer a durable Prefect deployment; fall back to
    an in-process asyncio task in dev (no Prefect server). Never blocks the turn."""
    payload = dict(
        job_id=str(job_id),
        sql=sql,
        db_config_json=_config_to_json(config),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        user_id=user_id,
        max_export_row_limit=config.max_export_row_limit,
        export_batch_size=config.export_batch_size,
    )
    try:
        from prefect.deployments import run_deployment  # type: ignore[import-untyped]

        await run_deployment(
            name="export-query/export-query",
            parameters=payload,
            timeout=0,  # fire-and-forget: return immediately, don't await completion
        )
        logger.info("Export job %s dispatched via Prefect deployment", job_id)
        return
    except Exception as exc:  # noqa: BLE001 — dev fallback when no Prefect server/deployment
        logger.warning("Prefect dispatch unavailable (%s); running export in-process (dev)", exc)

    from backend.app.flows.export import export_query_flow

    task = asyncio.create_task(export_query_flow(**payload))
    _PENDING_EXPORT_TASKS.add(task)
    task.add_done_callback(_PENDING_EXPORT_TASKS.discard)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_export_dispatch.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/export_dispatch.py backend/tests/test_export_dispatch.py
git commit -m "feat(backend): ExportDispatched signal + create/dispatch export job (Phase 3 T5)"
```

---

## Task 6: Wire the export band into the pipeline (replace ValueError offload)

**Files:**
- Modify: `backend/app/query/pipeline.py:1362-1426` (`_offload_to_export` body + routing) and the two `_execute_sql` call sites (`pipeline.py:2227-2305`)
- Modify: `backend/tests/test_massive_export.py` (adapt routing tests; drop worker-contract tests)
- Test: `backend/tests/test_pipeline_export_event.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_pipeline_export_event.py
"""The export band raises ExportDispatched; _execute_sql creates+dispatches a job;
process_query turns the signal into an `export` SSE event WITHOUT self-correcting."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.db import DatabaseType, DBConfig
from backend.app.query.export_dispatch import ExportDispatched


def _cfg(max_row_limit=1000):
    return DBConfig(
        db_type=DatabaseType.POSTGRESQL, host="db", port=5432, database="w",
        username="u", password="p", max_row_limit=max_row_limit,
    )


@pytest.mark.asyncio
async def test_export_band_raises_export_dispatched_and_creates_job():
    from backend.app.query import pipeline

    fake_job_id = uuid.uuid4()
    db = AsyncMock()
    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_cfg())),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": 5_000_000})),
        patch.object(pipeline, "create_export_job", new=AsyncMock(return_value=fake_job_id)),
        patch.object(pipeline, "dispatch_export_job", new=AsyncMock(return_value=None)) as dispatch,
    ):
        with pytest.raises(ExportDispatched) as exc:
            await pipeline._execute_sql(
                sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
                db=db, user_id="u1", question="all orders",
            )
    assert exc.value.job_id == fake_job_id
    assert exc.value.estimated_rows == 5_000_000
    dispatch.assert_awaited_once()


def test_export_event_shape():
    """_export_event yields a queued `export` SSE event carrying the job id."""
    from backend.app.query import pipeline

    fake_job_id = uuid.uuid4()
    event = pipeline._export_event(fake_job_id, 5_000_000)
    assert event["event"] == "export"
    data = json.loads(event["data"])
    assert data["export_job_id"] == str(fake_job_id)
    assert data["status"] == "queued"
    assert data["estimated_rows"] == 5_000_000
```

NOTE: the second test pins the new `_export_event` helper (a pure function) so the SSE shape is locked without driving the entire `process_query` generator (which needs Redis, an LLM, etc.). A full generator-level integration check is covered by the live smoke at Step 7.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_pipeline_export_event.py -q`
Expected: FAIL — `create_export_job`/`dispatch_export_job`/`_export_event` not imported/defined in `pipeline`; `_offload_to_export` still raises `ValueError`.

- [ ] **Step 3: Add imports + the `_export_event` helper, and rewire `_offload_to_export`**

In `backend/app/query/pipeline.py`, add module-top imports alongside the other `backend.app.query` imports:

```python
from backend.app.query.export_dispatch import (
    ExportDispatched,
    create_export_job,
    dispatch_export_job,
)
```

Ensure `import uuid` is present at module scope (it is imported locally at `pipeline.py:1363` inside the `try`; add a top-level `import uuid` so `_export_event`'s annotation and the helper work regardless). Confirm with `grep -n "^import uuid\|^import uuid as" backend/app/query/pipeline.py` — note the file already uses `import uuid as _uuid` at top for `_uuid.UUID`; reuse `_uuid` rather than adding a duplicate.

Add the SSE-shape helper at module level (after `_inject_row_limit`, ~line 970):

```python
def _export_event(job_id: "_uuid.UUID", estimated_rows: int) -> dict:
    """SSE event announcing an async CSV export job (replaces the ValueError hack)."""
    return {
        "event": "export",
        "data": json.dumps(
            {
                "export_job_id": str(job_id),
                "status": "queued",
                "estimated_rows": estimated_rows,
                "message": (
                    f"Your query returned ~{estimated_rows:,} rows — too large to display. "
                    "Preparing a CSV export; the download link will appear here when ready."
                ),
            }
        ),
    }
```

(`json` is already imported at module top — it's used throughout `process_query`. Verify with `grep -n "^import json" backend/app/query/pipeline.py`.)

Replace the `_offload_to_export` closure (currently `pipeline.py:1377-1402`). It still annotates `-> NoReturn` (it always raises). Remove the old worker import at `pipeline.py:1366` (`from backend.app.worker.tasks import export_massive_query_to_minio`):

```python
        async def _offload_to_export() -> NoReturn:
            # Export band (Phase 3): persist a durable job, dispatch the streaming
            # Prefect flow, and signal the pipeline generator to emit an `export`
            # SSE event. The flow streams the bounded sql in batches and truncates
            # at max_export_row_limit. We bound the DB scan here too by injecting
            # FETCH FIRST (export_ceiling + 1) so the cursor stops early.
            if db is None:
                # No session to record the job (e.g. schema-path). Fail safe with a
                # plain message rather than half-dispatching an untracked export.
                await _audit(success=False, error="export requires a db session", mem_trace=mem_trace)
                raise ValueError(
                    f"Query returned ~{estimated_rows:,} rows (too large to display); "
                    "exports are unavailable in this context."
                )
            export_sql = _inject_row_limit(transformed_sql, config.db_type, export_ceiling)
            job_id = await create_export_job(
                db,
                workspace_id=workspace_id or "default",
                user_id=user_id,
                conversation_id=f"{workspace_id}_{user_id}" if workspace_id else None,
                question=question,
                sql=export_sql,
                total_estimate=int(estimated_rows or 0),
            )
            await db.commit()  # make the queued row durable before dispatch
            await dispatch_export_job(
                job_id=job_id,
                sql=export_sql,
                config=config,
                workspace_id=workspace_id or "default",
                conversation_id=f"{workspace_id}_{user_id}" if workspace_id else None,
                user_id=user_id,
            )
            await _audit(success=True, row_count=int(estimated_rows or 0), mem_trace=mem_trace)
            raise ExportDispatched(job_id=job_id, estimated_rows=int(estimated_rows or 0))
```

The two routing call sites (`pipeline.py:1411` and `:1425`) are unchanged — they still `await _offload_to_export()`, which now raises `ExportDispatched`. After editing, `grep -n "export_massive_query_to_minio" backend/app/query/pipeline.py` should return nothing.

- [ ] **Step 4: Catch `ExportDispatched` in `process_query` (both call sites)**

At the first `_execute_sql` call site (`pipeline.py:2227-2241`), add a dedicated `except ExportDispatched` clause **before** the generic `except Exception` so the export signal never triggers self-correction:

```python
    rows: list[dict] = []
    try:
        from sqlalchemy.ext.asyncio import AsyncSession as _ExecSession

        async with _ExecSession(engine) as sess:
            rows = await _execute_sql(
                sql, engine, workspace_id=workspace_id, db=sess, user_id=user_id,
                question=request.question, explanation=explanation,
                mem_trace=mem_trace, team_id=team_id,
            )
    except ExportDispatched as exp:
        yield _export_event(exp.job_id, exp.estimated_rows)
        yield {"event": "done", "data": json.dumps({"conversation_id": cid})}
        return
    except Exception as e:
        logger.warning("SQL execution failed. Attempting LLM self-correction. Error: %s", e)
        # ... existing self-correction body unchanged down to the re-execute ...
```

At the post-correction re-execute (`pipeline.py:2284-2305`), wrap the same way so a (rare) huge corrected query also exports cleanly. The existing structure is `try: <generate+verify+re-execute> except Exception as retry_e: <error event>`. Wrap just the re-execute call with its own `except ExportDispatched`:

```python
            # Re-execute the corrected SQL
            try:
                async with _ExecSession(engine) as sess:
                    rows = await _execute_sql(
                        sql, engine, workspace_id=workspace_id, db=sess, user_id=user_id,
                        question=request.question, explanation=explanation,
                        mem_trace=mem_trace, team_id=team_id,
                    )
            except ExportDispatched as exp:
                yield _export_event(exp.job_id, exp.estimated_rows)
                yield {"event": "done", "data": json.dumps({"conversation_id": cid})}
                return
        except Exception as retry_e:
            logger.exception("SQL self-correction failed")
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": f"Query execution failed after correction attempt: {retry_e}"}
                ),
            }
            return
```

(The `done` event shape matches the existing terminal event at `pipeline.py:2031`.)

- [ ] **Step 5: Adapt `test_massive_export.py`**

The 3 worker-contract tests (`test_export_returns_download_url`, `test_export_zero_rows_returns_no_url`, `test_export_failure_is_reported_not_swallowed`) pin `export_massive_query_to_minio`, which the pipeline no longer calls. Delete them (leave a one-line comment that the worker module is now dead from the chat path → remove in Phase 4 cleanup). Rewrite the routing helper + export-band tests so the export band raises `ExportDispatched`:

```python
# Replace _run_routed and the export-band tests in backend/tests/test_massive_export.py
import uuid as _uuid
from backend.app.query.export_dispatch import ExportDispatched


async def _run_routed(estimated_rows: int, rows_returned: list | None = None, job_id=None):
    """Drive _execute_sql past routing. EXPLAIN returns `estimated_rows` for the
    BARE sql; create/dispatch are mocked so the export band raises ExportDispatched."""
    from backend.app.query import pipeline

    if rows_returned is None:
        rows_returned = [{"x": 1}]
    job_id = job_id or _uuid.uuid4()
    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        # db is an AsyncMock (export path needs a session) → stub vault-policy
        # resolution, which the bare AsyncMock can't satisfy.
        patch.object(pipeline, "_resolve_vault_policy", new=AsyncMock(return_value=None)),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": estimated_rows})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=rows_returned)),
        patch.object(pipeline, "create_export_job", new=AsyncMock(return_value=job_id)),
        patch.object(pipeline, "dispatch_export_job", new=AsyncMock(return_value=None)),
    ):
        return await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=AsyncMock(), user_id="u1", question="show all orders",
        )


@pytest.mark.asyncio
async def test_estimate_above_display_limit_dispatches_export():
    """R̂ > max_row_limit → export band raises ExportDispatched with the estimate."""
    jid = _uuid.uuid4()
    with pytest.raises(ExportDispatched) as exc:
        await _run_routed(estimated_rows=50_000, job_id=jid)
    assert exc.value.job_id == jid
    assert exc.value.estimated_rows == 50_000


@pytest.mark.asyncio
async def test_huge_estimate_dispatches_instead_of_blocking():
    """Phase 2 removed the >100x hard block; a huge estimate routes to export."""
    with pytest.raises(ExportDispatched):
        await _run_routed(estimated_rows=5_000_000)


@pytest.mark.asyncio
async def test_inline_safety_cap_dispatches_when_read_overflows():
    """EXPLAIN underestimates (≤ max_row_limit) but the read returns max_row_limit+1
    rows → switch to export band."""
    over = [{"x": i} for i in range(1001)]  # max_row_limit(1000) + 1
    with pytest.raises(ExportDispatched):
        await _run_routed(estimated_rows=200, rows_returned=over)
```

Update `test_estimate_within_display_limit_returns_rows_inline` so it no longer references the worker; assert `create_export_job` is NOT called:

```python
@pytest.mark.asyncio
async def test_estimate_within_display_limit_returns_rows_inline():
    """R̂ ≤ max_row_limit (1000) → display path returns rows, no export job."""
    from backend.app.query import pipeline

    create = AsyncMock()
    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        # db is an AsyncMock (export path needs a session) → stub vault-policy
        # resolution, which the bare AsyncMock can't satisfy.
        patch.object(pipeline, "_resolve_vault_policy", new=AsyncMock(return_value=None)),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": 50})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=[{"x": 1}, {"x": 2}])),
        patch.object(pipeline, "create_export_job", new=create),
    ):
        out = await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=AsyncMock(), user_id="u1", question="q",
        )
    assert out == [{"x": 1}, {"x": 2}]
    create.assert_not_called()
```

Delete `test_offload_failure_asks_user_to_narrow_query` (the failure path is now owned by the flow → `status=error`, covered by `test_export_flow.py::test_flow_marks_error_when_stream_raises`).

- [ ] **Step 6: Run the affected suites**

Run: `cd backend && uv run pytest tests/test_pipeline_export_event.py tests/test_massive_export.py -q`
Expected: PASS. Then the broader slice: `cd backend && uv run pytest tests/ -q -k "export or pipeline or massive or stream"`.

- [ ] **Step 7: Live smoke (real Oracle, real MinIO)**

Restart the backend so the container loads the new code:

```bash
docker restart aria-backend
```

Then in the Playwright-driven Chrome (logged into `aria.localhost`), ask stc-kuwait: "show all rows from FCT_PREP_USAGE_BIG". Confirm via `docker logs aria-backend` and psql:

```bash
docker exec -i aria-postgres psql -U aria -d aria -c \
  "SELECT id,status,row_count,truncated,left(download_url,40) FROM export_jobs ORDER BY created_at DESC LIMIT 3;"
```

Expect: a `queued` row appears, the chat bubble shows the `export` "preparing CSV" message (NOT a red "Query execution failed"), the flow advances the row to `success` with `row_count=100000`, `truncated=true`, a non-null `download_url`, and NO duplicate export / self-correction in the logs. (The `download_url` still embeds the internal `minio:9000` host — the browser-reachability fix is Phase 4's download proxy. Phase 3's bar: durable job + clean event + streamed, capped CSV in MinIO.)

- [ ] **Step 8: Commit**

```bash
git add backend/app/query/pipeline.py backend/tests/test_massive_export.py backend/tests/test_pipeline_export_event.py
git commit -m "feat(backend): dispatch async streaming export from chat; emit export SSE event (Phase 3 T6)"
```

---

## Task 7: DoD gate + memory + handoff

**Files:**
- Modify: `~/.claude/projects/-Users-tunasonmez-projects-b2metric-aria/memory/massive-export-feature.md` + `MEMORY.md`

- [ ] **Step 1: Run the full backend suite (regression net before the gate)**

Run: `cd backend && uv run pytest tests/ -q`
Expected: all green. The prior baseline was 324 passed; Phase 3 adds ~13 tests and removes 4 worker-contract/offload-failure tests.

- [ ] **Step 2: Run the DoD gate**

Run: `bash smoke/done-check.sh`
Expected: "✓ Definition of Done met". If the E2E/smoke steps skip because the backend isn't on `localhost:8000`, that is the known env-dependence noted in the spec — the real boot+login smoke is `bash smoke/check.sh`.

- [ ] **Step 3: Update the feature memory**

Edit `massive-export-feature.md`: mark Phase 3 DONE (streaming `stream_query` + `upload_csv_stream` + `export_query` flow + `export_jobs` + chat dispatch via `ExportDispatched`/`export` SSE event); record the new alembic head; note the two follow-ups now PARTLY addressed (error-UX fixed: no more ValueError/self-correction/duplicate; broken-URL still open → Phase 4 download proxy). Update the `MEMORY.md` one-liner accordingly.

- [ ] **Step 4: Commit**

```bash
SKIP_TDD_GUARD=1 git add -A
git commit -m "docs(memory): massive-export Phase 3 done — streaming export + async dispatch"
```
(`SKIP_TDD_GUARD` justified: memory/docs only, no backend logic change.)

- [ ] **Step 5: Offer Phase 4**

Phase 4 (spec §D delivery surfaces): `GET /api/exports` (list, RBAC workspace-scoped) + `GET /api/exports/{id}` (status poll) + `GET /api/exports/{id}/download` (proxy → 302 presigned, fixing the browser-unreachable `minio:9000` URL); FE: `/exports` page + inline download button in the chat bubble keyed off `export_job_id` + completion badge. Also register the `export-query` Prefect deployment in the prod worker so dispatch is durable (not the dev asyncio fallback). Write as `docs/superpowers/plans/2026-07-..-massive-export-phase4-delivery.md`.

---

## Self-Review

**Spec coverage (§C + §D durable-record + dispatch):**
- §C.1 executor streaming → Task 2 (`stream_query` per dialect). ✔
- §C.2 bounded query + truncation signal → Task 4 (`_capped_batches`, `truncated`) + Task 6 (`_inject_row_limit(export_ceiling)` bounds the DB scan). ✔
- §C.3 streaming CSV → MinIO multipart → Task 3 (`upload_csv_stream` + `_IteratorIO`). ✔
- §C.4 Prefect flow → Task 4 (`export_query_core` + `get_export_flow`). ✔
- §C.5 durability → Task 5 (`run_deployment` in prod, asyncio fallback in dev) + Task 7 Step 5 (register deployment). ✔
- §D durable record → Task 1 (`export_jobs` + model). ✔
- §D dispatch + inline SSE → Task 6 (`export` event + `export_job_id`). ✔
- §D API endpoints / Exports page / download proxy → **Phase 4** (out of scope, offered in Task 7 Step 5). ✔ (intentional boundary)
- §E error handling: stream error → job `error` (Task 4 test); EXPLAIN-fail → display path (unchanged Phase 2 behavior); truncation = success+flag (Task 4 test). ✔

**Placeholder scan:** no TBD / "handle errors appropriately" / "similar to Task N" — every code step is complete and self-contained. ✔

**Type consistency:** `ExportStatus` values (`queued/running/success/error`) match the migration `server_default="queued"` and the `String(16)` column. `ExportDispatched(job_id=, estimated_rows=)` is constructed identically in Task 5, Task 6, and the tests. `export_query_core(**kwargs)` keyword signature matches the test calls and `export_query_flow`'s call. `stream_query(sql, params=None, *, batch_size)` is consistent across executors, `stream_query_sync`, and `_capped_batches`'s input. `upload_csv_stream(batches, *, key)` matches its test and the flow call. `_export_event(job_id, estimated_rows)` matches its test and both call sites. ✔

---

## Risks & Watch-outs

- **`status` as `String(16)` vs PG enum:** chosen to avoid a second enum type + simpler migration; `StrEnum` round-trips as the stored string. If the team prefers a PG enum for parity with `database_type`, that's a deliberate larger change — keep `String(16)` for Phase 3.
- **`run_deployment` needs a registered `export-query` deployment** in prod; until it exists, dispatch falls back to the in-process asyncio task (dev parity, non-durable). Registering the deployment is a deploy-time step (mirror how `reconcile` is registered) — flagged in Task 7 Step 5, NOT a code task here.
- **`db.commit()` inside `_offload_to_export`:** the queued row must be durable before dispatch (so the flow finds it). The surrounding `_ExecSession` in `process_query` is dedicated to this `_execute_sql` call, and the export path raises immediately after committing — no later code assumes an open transaction. Verify no audit write after the commit is lost (the `_audit` call is before the raise and uses the same session; ensure it is flushed/committed — `_audit` opens its own AuditService on `db`; if it needs a commit, the trailing `await db.commit()` already covered the job insert, so move the `_audit` call before the `db.commit()` OR add a second commit after `_audit`). **Decision:** order is create_job → `db.commit()` → dispatch → `_audit` → raise; add `await db.commit()` after `_audit` so the audit row persists too.
- **SQLite in tests vs Postgres in prod:** model/flow/dispatch tests use `sqlite+aiosqlite`. `UUID(as_uuid=True)` + no JSONB on `export_jobs` keeps it SQLite-compatible. If the project's harness already provides a Postgres test-DB fixture (grep `backend/tests/conftest.py` for an `engine`/`session` fixture), prefer it for full fidelity.
- **`aiosqlite` availability:** if not installed, add it as a dev dependency or switch the four DB-backed tests to the existing async test-DB fixture. Check first: `grep -rn "aiosqlite\|sqlite+aiosqlite" backend/tests/`.
- **`_get_engine` import in the flow:** `export_query_flow` imports `_get_engine` from `backend.app.api.query` exactly as `reconcile.py` does. If that symbol moved, mirror `reconcile.py`'s current import.
