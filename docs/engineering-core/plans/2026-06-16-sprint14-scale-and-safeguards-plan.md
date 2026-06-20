# Sprint 14: EXPLAIN Guards, Large Result Pipelines, and Architecture Scale

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development or engineering-core:executing-plans to implement this plan task-by-task.

**Goal:** Provide ultimate protection against massive rogue SQL queries by introducing EXPLAIN-based safeguards before execution, and establish the background job pipeline (Prefect + MinIO) to asynchronously process and serve enormous datasets to the user.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL/Oracle/MySQL, Prefect (or ARQ for background tasks), MinIO.

---

### Task 1: EXPLAIN Dry-Run & Row Estimation Safeguard
*Goal: Intercept expensive LLM-generated SQL queries before they lock the database.*

**Files:**
- Modify: `backend/app/db/executor.py`
- Modify: `backend/app/query/pipeline.py`

- [x] **Step 1: DB Executor `explain()` method**
In `executor.py`, add an `async def explain(sql: str, config: DBConfig) -> dict` abstract interface. Implement it for `PostgreSQLExecutor` (`EXPLAIN (FORMAT JSON) ...`), `OracleExecutor` (`EXPLAIN PLAN FOR ...`), etc. It should return a unified dict containing at least `{"estimated_rows": 5000000, "estimated_cost": 1234}`. **(RESOLVED)**
- [x] **Step 2: Guard Integration**
In `pipeline.py`, right before `await execute_query(...)`, call the new `explain()` method. Compare the `estimated_rows` against the tenant's `max_row_limit` (with some safety multiplier, e.g., 2x). If the estimate wildly exceeds limits or triggers cost thresholds, cancel the execution and return a safe error message to the LLM (for self-correction) or the user. **(RESOLVED)**

---

### Task 2: Background Worker Execution for Large Results
*Goal: When a query is permitted but its result set exceeds UI limits (e.g. >10,000 rows), do not crash the SSE stream. Offload it.*

**Files:**
- Create/Modify: `backend/app/worker/tasks.py` (Prefect or ARQ tasks)
- Modify: `backend/app/query/pipeline.py`

- [x] **Step 1: Background Data Export Task**
Create an async background worker task (`export_massive_query_to_minio`). It takes the SQL, executes it asynchronously in batches/cursors, writes directly to a temporary CSV file, and uploads it to MinIO. **(RESOLVED)**
- [x] **Step 2: Pipeline Offload Logic**
In `pipeline.py`, if the result (or EXPLAIN estimate) sits between the UI threshold (e.g., 2,000 rows) and the hard `max_row_limit` (e.g., 100,000 rows), do not `fetchall()`. Instead, dispatch the background task, and yield an SSE event like: `"This query returned 50,000 rows. Processing in background..."`. Return the MinIO presigned download link to the user once the worker finishes. **(RESOLVED)**

---

### Task 3: Admin Health UI Polishing & Metrics Expand
*Goal: Make the Admin Health page more robust.*

**Files:**
- Modify: `frontend/src/app/admin/health/page.tsx`
- Modify: `backend/app/api/endpoints/admin/health.py`

- [x] **Step 1: Prefect / ARQ Health Check** — added a `background_worker` entry to `/api/admin/health`. The large-result export is fire-and-forget via in-process `asyncio.create_task` (no external ARQ/Prefect broker wired — `arq` is declared but unused), so the probe (`_check_background_worker`) verifies the *actual* mechanism: the event loop can schedule + complete a background task (times out if wedged). Unit-tested. **(RESOLVED)**
- [x] **Step 2: DB Connection Tests** — the backend already pings each active tenant customer DB (`customer_dbs`: `SELECT 1`, scoped to the caller's own `customer_id`), and the Health dashboard already renders it ("Customer Databases") via its generic service grid. Verified present; no change needed beyond confirming coverage. **(RESOLVED)**

> **Note:** No frontend change was required — `frontend/src/app/admin/health/page.tsx` renders every service key in the response generically (CSS `capitalize`), so the new `background_worker` card appears automatically as "Background Worker".

---

### Task 4: Extend CI ruff coverage to `agents/`
*Goal: Close a lint-gate blind spot — the "Lint Backend (ruff)" job only checks `backend/`, so the top-level `agents/` package (chart pipeline, artifact store/vault) is never linted.*

**Files:**
- Modify: `.github/workflows/ci.yml` (lint-backend job)
- Modify: `agents/**` (fix surfaced findings)

- [x] **Step 1: Add `agents/` to the ruff invocation**
Update the `lint-backend` job to run `ruff check backend/ agents/` and `ruff format --check backend/ agents/` so the chart/artifact agents are gated like the rest of the backend. **(RESOLVED)**
- [x] **Step 2: Fix the ~22 pre-existing findings** — fixed 24 findings (UP037/F401/UP017/I001 auto-fixed; F841 unused `loop` + UP042 `ChartType` → `StrEnum` by hand) + `ruff format agents/`. `ruff check backend/ agents/` clean; unit gate 263 passed. **(RESOLVED)**
`uv run ruff check agents/` currently reports ~22 errors (unused imports, import ordering, etc.; most are `--fix`-able). Fix them until `agents/` is clean, then keep it in the gate. Surfaced 2026-06-20 while dropping `pydantic-ai` from `agents/chart_llm.py` (PR #47).