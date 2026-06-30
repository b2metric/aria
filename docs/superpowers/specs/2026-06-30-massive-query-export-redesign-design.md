# Massive-Query Export Redesign — Two Thresholds + Batched Async CSV

**Date:** 2026-06-30
**Status:** Design (approved sections A–E; pending written-spec review)
**Branch (work):** TBD (cut from `feat/adopt-b2m-ui` or `main`)

## Problem

The "huge result → MinIO CSV link" feature is effectively dead from the chat path,
and even when it would fire it is unsafe:

1. **Single overloaded threshold.** `customer_db_configs.max_row_limit` is used for
   *both* the UI display cap *and* the offload trigger. There is no separate notion
   of "how many rows may be exported".
2. **The offload never triggers from chat.** The SQL-generation prompt
   (`llm_sql.py`) instructs the model: *"Always include reasonable limits (default:
   FETCH FIRST 100 ROWS ONLY)"*. The model therefore emits its own row cap; the
   pipeline sees an existing limit and skips its injection; `EXPLAIN` then runs on
   the already-limited SQL and the estimate is capped at that small value — never
   exceeding the 5000 `UI_RENDER_THRESHOLD`. Empirically confirmed on live Oracle:
   `FCT_PREP_USAGE_BIG` (1,000,000 rows) → `EXPLAIN` of `… FETCH FIRST 1001` returns
   `1001`; bare query returns `1,000,000`.
3. **The export is unbounded in memory.** `export_massive_query_to_minio` calls
   `execute_query_sync(sql)` which loads *all* rows into RAM, builds the entire CSV
   in a `StringIO`, then uploads — and it is itself passed the limited
   `transformed_sql`, so the "full export" is actually capped at the row limit.

## Goals

- Separate **display** and **export** ceilings, both tenant-configurable in the UI.
- Make routing decisions on the **true** result size, respecting genuine user intent
  (a "top 100" question must still render 100 rows inline).
- Produce exports by **streaming in batches** — bounded DB scan, bounded driver
  round-trips, bounded memory — never loading the whole dataset.
- Deliver exports **asynchronously** (Prefect), non-blocking, durable across restarts,
  surfaced both inline in chat and in a persistent Exports list.

## Non-Goals

- Changing RBAC / SQL-visibility / row-limit invariants in `AGENTS.md` (we extend,
  not relax them).
- Formats other than CSV (no XLSX/Parquet in this iteration — YAGNI).
- Scheduled/recurring exports.

## Decisions (from brainstorming)

| # | Decision |
|---|----------|
| A | Two FE-set ceilings + batch size on `customer_db_configs`. |
| B | Overflow beyond the export ceiling → **truncate to ceiling + warn** (not block). |
| C | Delivery is an **async Prefect flow** (queued → link when ready). |
| D | Routing by **EXPLAIN of the bare (true-intent) SQL** + inline safety cap. |
| E | Link reaches the user **both** inline in chat **and** in a persistent Exports area. |

---

## A. Two thresholds + configuration

Two configurable **ceilings** plus a batch size, all tenant-scoped on
`customer_db_configs`, all editable as separate inputs in **Admin → Tenant Config**:

| Field | Meaning | Default | FE input |
|-------|---------|---------|----------|
| `max_row_limit` *(existing, kept)* | **display ceiling** | 1,000 | existing input |
| `max_export_row_limit` *(new)* | **export ceiling** | 100,000 | new input "Max Rows per Export (CSV)" |
| `export_batch_size` *(new)* | DB read batch (`fetchmany`) | 50,000 | new input "Export Batch Size" |

**Band semantics** for a query whose true result size is `R`:

```
R ≤ max_row_limit                        → render inline             (R = "per_query")
max_row_limit < R ≤ max_export_row_limit → export all R rows to CSV  (R = "per_export")
R > max_export_row_limit                 → export first max_export_row_limit rows + "truncated" warning
```

So by construction: `per_query ≤ max_row_limit < per_export ≤ max_export_row_limit`.
(`per_query`/`per_export` are runtime actual counts; the two `*_limit`s are the
configured ceilings.)

**Config invariants** (Pydantic `Field` + cross-field validator on the tenant API,
mirrored client-side):
- `max_row_limit ≤ max_export_row_limit ≤ 1,000,000`
- `export_batch_size ≤ max_export_row_limit`
- `max_row_limit` has **no lower floor** (the previous `ge=100` is removed); `≥ 1`.
- `1,000,000` stays as the hard product ceiling for both limits.

**Migration:** Alembic adds the two columns to `customer_db_configs`; backfill
`max_export_row_limit = max(max_row_limit, 100000)`, `export_batch_size = 50000`.
`DBConfig` dataclass gains both fields (defaulted, backward compatible).
`PUT /admin/tenant` accepts/serializes all three; older single-field callers still work.

## B. Routing logic (which band)

**Root-cause fix (prompt):** remove the `llm_sql.py` rule *"Always include reasonable
limits (default: FETCH FIRST 100 ROWS ONLY)"*. The model then adds a row limit **only
when the user's question implies one** ("top N", "first N"). Any limit remaining in
the generated SQL is therefore user-intended.

**Ordering fix (pipeline):** run the routing `EXPLAIN` on the **as-generated SQL**,
*before* the pipeline injects its own safety limit. Call the estimate `R̂`.

**Route by `R̂`:**

| `R̂` | Path |
|------|------|
| `R̂ ≤ max_row_limit` | **display** — execute with `FETCH FIRST max_row_limit+1`, render |
| `R̂ > max_row_limit` | **export** — create job, dispatch Prefect flow, return "queued" |

- "top 100" → model emits `FETCH FIRST 100` → `R̂ = 100` → display. ✔
- "all rows" → no limit → `R̂ =` full table → export. ✔

**Inline safety cap (display path):** `EXPLAIN` can underestimate (stale stats). The
display query runs with `FETCH FIRST max_row_limit+1`; if it returns exactly
`max_row_limit+1` rows, the true `R` exceeds the display ceiling → **abort inline,
create an export job, return "queued"**. (EXPLAIN drives routing; the read verifies.)

**Remove the old `R̂ > 100 × max_row_limit` hard block.** Batched streaming + the
`max_export_row_limit` truncation make arbitrarily large queries safe; we truncate +
warn instead of blocking. Keep a `log.info` of large estimates.

**Defensive fallback:** if, despite the prompt change, the model emits a spurious
trailing limit and the user's question shows no top-N/first-N intent, strip that
trailing `FETCH FIRST … ROWS ONLY` / `LIMIT …` / `TOP …` for the `EXPLAIN` only
(sqlglot Limit node removal, regex fallback). Secondary safeguard, not the primary
mechanism.

**If `EXPLAIN` fails** (cannot estimate): fall through to the display path and rely on
the inline safety cap — never block a query because estimation failed.

## C. Batched streaming export (Prefect flow)

Bound three things at once: DB scan (server-side limit), driver round-trips (batch),
memory (streaming upload).

**1. Executor streaming method** — alongside `execute`/`explain`, add
`stream_query(sql, config, batch_size) -> Iterator[list[dict]]`:
- Oracle (`oracledb`): set `cur.arraysize = batch_size`, loop `fetchmany(batch_size)`.
- Postgres (`psycopg2`): **server-side named cursor** (`itersize = batch_size`) so the
  client does not buffer the full result.
- MySQL (`pymysql`): `SSCursor` (unbuffered) + `fetchmany`.
- MSSQL (`pymssql`): `fetchmany`.

**2. Bounded query + truncation signal.** Export SQL = **bare_sql** (no display limit)
+ `FETCH FIRST (max_export_row_limit + 1) ROWS ONLY` so the DB stops early. Stream in
batches; write the first `max_export_row_limit` rows; if the `+1`-th row exists →
`truncated = True`.

**3. Streaming CSV → MinIO multipart.** Wrap the batch iterator in a lazy CSV-bytes
generator; adapt it as an `io.RawIOBase` stream and hand it to MinIO
`put_object(..., length=-1, part_size=10MB)`, which uploads multipart. Neither the full
CSV nor the full result set is ever held in memory or on disk. New
`ArtifactStore.upload_csv_stream(...)`. Safe value coercion (Decimal/datetime/None →
str) per cell.

**4. Prefect flow (on-demand)** — `app/flows/export.py`, following `reconcile.py`:
`@flow export_query_flow(job_id, sql, workspace_id, conversation_id, user_id,
max_export_row_limit, batch_size)`. Steps: mark job `running` → open stream → write to
MinIO → mint 3-day presigned/public URL → mark job `success` (row_count, truncated,
url) or `error`. The chat pipeline triggers it via `run_deployment` (async).

**5. Durability.** Flow state lives in Prefect; a backend restart does not kill an
export (same philosophy as the existing reconcile flow).

## D. Status tracking + link delivery

**Durable record** — new Postgres table `export_jobs` (Alembic):
`id (uuid), workspace_id, user_id, conversation_id, question, sql, status
(queued|running|success|error), row_count, truncated, total_estimate, minio_key,
download_url, error, prefect_flow_run_id, created_at, started_at, completed_at`.

**Flow:** routing picks the export band → insert `export_jobs` row (`queued`) →
`run_deployment(export_query_flow, job_id=…)` → emit a chat SSE `export` event
("~R rows — too large to display, preparing CSV…") and attach `export_job_id` to the
assistant message → chat turn ends immediately (non-blocking). The flow advances the
row through its lifecycle.

**Delivery (both):**
- **Inline chat:** the assistant message carries `export_job_id`; the FE polls
  `GET /api/exports/{job_id}` (or rides the existing SSE/run-resume channel) until
  `success` → renders a **download button in the same bubble**; on `error` → message.
- **Persistent Exports page:** new FE route `/exports` → `GET /api/exports`
  (workspace-scoped, RBAC) lists recent jobs with status + link; a badge notifies on
  completion.
- **Download:** `GET /api/exports/{job_id}/download` proxy → 302 to the presigned MinIO
  URL (access control + audit rather than handing out the raw link).

**RBAC / visibility:** export jobs are workspace-scoped and honor the existing
RBAC/SQL-visibility invariants; the download proxy verifies the caller's workspace
membership.

## E. Error handling & testing

**Error handling:**
- Flow failure → job `error`; surfaced inline and in the Exports list ("export failed,
  narrow the query / retry").
- DB stream interruption mid-flight → **abort the multipart upload**; never deliver a
  half-written CSV link; job `error`.
- MinIO upload failure → job `error`.
- `EXPLAIN` failure → display path + safety cap (never block on estimation failure).
- Truncation is a **success** with `truncated=true` + warning, not an error.
- Export jobs are logged via `AuditService` (governance).

**Testing (TDD):**
- *Routing:* prompt no longer auto-limits; "top N" → display; no-limit → export;
  inline safety cap trips → export; EXPLAIN-fail → display.
- *Streaming:* `stream_query` per executor (mock cursor `fetchmany`) yields batches and
  honors `batch_size`.
- *Truncation:* stream of `max_export+1` → exactly `max_export` rows written,
  `truncated=true`.
- *CSV:* streaming generator emits correct header + rows + value coercion.
- *Config:* invariant validation (`max_row_limit ≤ max_export_row_limit ≤ 1M`,
  `batch_size ≤ max_export`); reject violations.
- *Jobs:* `export_jobs` lifecycle queued → success(url) / error.
- *Flow:* `export_query_flow` end-to-end with mocked DB stream + mocked MinIO.
- *API:* `GET /api/exports` RBAC workspace scoping; `GET /api/exports/{id}`.
- *Manual/E2E:* on a workspace with a granted large table, "all rows from
  FCT_PREP_USAGE_BIG" → queued → link appears inline + in Exports list → download →
  row count matches (capped at `max_export_row_limit`).
- Existing `test_massive_export.py` (worker contract + pipeline-branch) adapted to the
  new flow.

**Migration / compatibility:**
- Alembic: add `max_export_row_limit`, `export_batch_size` to `customer_db_configs`;
  create `export_jobs`; backfill defaults.
- The inline `export_massive_query_to_minio` worker is replaced by the Prefect flow.
- `llm_sql.py` prompt change is locked by the routing tests.

## Affected components

- `backend/app/query/llm_sql.py` — remove the auto-limit prompt rule.
- `backend/app/query/pipeline.py` — reorder EXPLAIN (bare SQL) + new routing + inline
  safety cap; drop the `100×` hard block; dispatch export job instead of inline export.
- `backend/app/db/executor.py` — `stream_query` per executor.
- `backend/app/db/models.py` (`DBConfig`) — two new fields.
- `backend/app/flows/export.py` *(new)* — Prefect export flow.
- `agents/artifact_store.py` (`ArtifactStore`) — `upload_csv_stream`.
- `backend/app/models/…` + Alembic — `export_jobs` table + `customer_db_configs` cols.
- `backend/app/api/endpoints/admin/tenant.py` — accept/validate the two new fields.
- `backend/app/api/…/exports.py` *(new)* — list / status / download-proxy endpoints.
- `frontend/src/app/admin/tenant-config/page.tsx` — two new inputs + validation.
- `frontend/src/app/exports/page.tsx` *(new)* — persistent Exports list.
- Chat message rendering — inline export status + download button.

## Open questions

- Exact location of the Exports page in the FE nav (top-level `/exports` vs under a
  "Data"/"History" section) — defer to implementation.
- Whether the download proxy also streams the file (full audit) or only 302-redirects
  to the presigned URL — start with redirect; revisit if audit needs the bytes.
