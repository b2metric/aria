# Massive-Export Phase 2 — Routing (true-size EXPLAIN + band decision) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the display-vs-export routing decide on the query's TRUE result size: stop the SQL-generator from auto-capping rows, run `EXPLAIN` on the as-generated SQL *before* the pipeline injects its display limit, route by the tenant's `max_row_limit` (not a hardcoded 5000), add an inline safety cap, and replace the absolute-block on huge estimates with the export band.

**Architecture:** Three changes in `backend/app/query/`: (1) drop the `llm_sql.py` "always add a limit" prompt rule so any limit in the SQL is user-intended; (2) extract the row-limit injection into a pure helper; (3) restructure `_execute_sql` so `EXPLAIN` runs on the un-limited SQL, routes by `max_row_limit`, injects the display limit only on the display path, offloads to the export band (bounded by `max_export_row_limit`) when the estimate exceeds the display ceiling OR the inline read overflows. The export band still calls the existing `export_massive_query_to_minio` — Phase 3 replaces that with a batched streaming Prefect flow.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2, pytest (+ pytest-asyncio), sqlglot, litellm. Oracle/Postgres/MySQL/MSSQL via the executor layer.

**Spec:** `docs/superpowers/specs/2026-06-30-massive-query-export-redesign-design.md` (section B). Depends on Phase 1 (config: `max_row_limit`, `max_export_row_limit` on `DBConfig` — already shipped).

---

## File Structure

- `backend/app/query/llm_sql.py` — `SYSTEM_PROMPT` rule 2: stop auto-limiting; honor only explicit "top N".
- `backend/app/query/pipeline.py` — new pure helper `_inject_row_limit(...)`; restructured `_execute_sql` routing block; removed 100× hard block.
- New/updated tests:
  - `backend/tests/test_row_limit_injection.py` — *new*, unit tests for `_inject_row_limit`.
  - `backend/tests/test_massive_export.py` — *update* the 3 existing pipeline-branch tests + add routing/safety-cap tests (this file already imports `pipeline` and `_pg_config`).
  - `backend/tests/test_llm_sql_prompt.py` — *new*, pins the prompt rule.

**Key invariant for routing:** route on `EXPLAIN` of the **bare** (dialect-transformed, NOT display-limited) SQL. `R̂ ≤ max_row_limit` → display; `R̂ > max_row_limit` → export. The display read still hard-stops at `max_row_limit + 1`; hitting that ceiling means the true size exceeds the display limit → export.

---

## Task 1: Stop the SQL generator from auto-limiting

**Files:**
- Modify: `backend/app/query/llm_sql.py:31` (`SYSTEM_PROMPT` rule 2)
- Test: `backend/tests/test_llm_sql_prompt.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_llm_sql_prompt.py`:

```python
"""Phase 2 — the SQL prompt must NOT auto-cap rows (only honor explicit top-N).

A default 'FETCH FIRST 100' instruction made the model emit its own limit, which
defeated the EXPLAIN-based routing (EXPLAIN saw the capped SQL). The pipeline owns
limiting now; the model only limits when the user explicitly asks for top/first N.
"""

from __future__ import annotations

from backend.app.query.llm_sql import SYSTEM_PROMPT


def test_prompt_does_not_instruct_a_default_row_limit():
    text = SYSTEM_PROMPT.lower()
    assert "default: fetch first 100" not in text
    assert "always include reasonable limits" not in text


def test_prompt_tells_model_not_to_self_limit():
    text = SYSTEM_PROMPT.lower()
    # The model is told the system applies limits; it only limits on explicit top-N.
    assert "do not add" in text and "limit" in text
    assert "top" in text  # explicit top-N / first-N intent is still honored
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_llm_sql_prompt.py -q`
Expected: FAIL — rule 2 currently says "Always include reasonable limits (default: FETCH FIRST 100 ROWS ONLY)".

- [ ] **Step 3: Replace prompt rule 2**

In `backend/app/query/llm_sql.py`, replace the line:

```
2. Always include reasonable limits (default: FETCH FIRST 100 ROWS ONLY)
```

with:

```
2. Do NOT add your own row limit — the system applies the row limit automatically.
   Only add `FETCH FIRST N ROWS ONLY` when the user EXPLICITLY asks for a specific
   count ("top 10", "first 50", "5 largest"). Otherwise return the query unlimited.
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_llm_sql_prompt.py -q`
Expected: PASS (2).

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/llm_sql.py backend/tests/test_llm_sql_prompt.py
git commit -m "feat(backend): stop SQL generator from auto-limiting rows (honor only explicit top-N)"
```

---

## Task 2: Extract a pure `_inject_row_limit` helper

**Files:**
- Modify: `backend/app/query/pipeline.py` (extract the inline injection at lines 1267-1275 into a module-level helper; stop injecting before EXPLAIN)
- Test: `backend/tests/test_row_limit_injection.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_row_limit_injection.py`:

```python
"""Phase 2 — pure row-limit injection helper (dialect-aware, skip-if-present)."""

from __future__ import annotations

from backend.app.db import DatabaseType
from backend.app.query.pipeline import _inject_row_limit


def test_oracle_appends_fetch_first():
    out = _inject_row_limit("SELECT * FROM t", DatabaseType.ORACLE, 1000)
    assert "FETCH FIRST 1001 ROWS ONLY" in out  # limit + 1


def test_non_oracle_appends_limit():
    out = _inject_row_limit("SELECT * FROM t", DatabaseType.POSTGRESQL, 1000)
    assert "LIMIT 1001" in out


def test_skips_when_oracle_limit_already_present():
    sql = "SELECT * FROM t FETCH FIRST 10 ROWS ONLY"
    assert _inject_row_limit(sql, DatabaseType.ORACLE, 1000) == sql


def test_skips_when_limit_or_top_already_present():
    assert _inject_row_limit("SELECT * FROM t LIMIT 10", DatabaseType.POSTGRESQL, 1000) == \
        "SELECT * FROM t LIMIT 10"
    assert _inject_row_limit("SELECT TOP 10 * FROM t", DatabaseType.MSSQL, 1000) == \
        "SELECT TOP 10 * FROM t"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_row_limit_injection.py -q`
Expected: FAIL — `ImportError: cannot import name '_inject_row_limit'`.

- [ ] **Step 3: Add the helper + stop pre-EXPLAIN injection**

In `backend/app/query/pipeline.py`, add this module-level helper (place it near `_transform_sql_for_dialect`, ~line 908). `DatabaseType` is already imported at module top, so use it directly:

```python
def _inject_row_limit(sql: str, db_type: DatabaseType, limit: int) -> str:
    """Append a dialect-correct ``limit + 1`` cap, unless the SQL already has one.

    The ``+1`` lets the caller detect overflow (got ``limit+1`` rows ⇒ there are
    more than ``limit``). Skips injection when the SQL already carries a
    FETCH FIRST / LIMIT / TOP (i.e. a user-intended explicit cap).
    """
    import re

    if db_type.value == "oracle":
        if not re.search(r"FETCH\s+FIRST", sql, re.IGNORECASE):
            return sql + f"\nFETCH FIRST {limit + 1} ROWS ONLY"
        return sql
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE) and not re.search(
        r"\bTOP\b", sql, re.IGNORECASE
    ):
        return sql + f"\nLIMIT {limit + 1}"
    return sql
```

Then, at the existing injection site (lines 1262-1275 inside `_execute_sql`), REPLACE:

```python
    # Apply row limits
    import re

    row_limit = getattr(config, "max_row_limit", 1000)

    # Simple limit injection for safety if the query doesn't already have one
    if config.db_type.value == "oracle":
        if not re.search(r"FETCH\s+FIRST", transformed_sql, re.IGNORECASE):
            transformed_sql += f"\nFETCH FIRST {row_limit + 1} ROWS ONLY"
    else:
        if not re.search(r"\bLIMIT\b", transformed_sql, re.IGNORECASE) and not re.search(
            r"\bTOP\b", transformed_sql, re.IGNORECASE
        ):
            transformed_sql += f"\nLIMIT {row_limit + 1}"
```

with:

```python
    row_limit = getattr(config, "max_row_limit", 1000)
    # NOTE (Phase 2): the display limit is NOT injected here anymore — EXPLAIN must
    # run on the un-limited SQL to estimate the true result size. The limit is
    # injected on the display path only, after routing (see the EXPLAIN block below).
```

(This leaves `transformed_sql` "bare" — dialect-transformed but un-limited — for the security guard and EXPLAIN. The security-guard block immediately below is unchanged; it operates on `transformed_sql` correctly whether or not a limit is present.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_row_limit_injection.py -q`
Expected: PASS (4).

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/pipeline.py backend/tests/test_row_limit_injection.py
git commit -m "refactor(backend): extract _inject_row_limit helper; stop pre-EXPLAIN limit injection"
```

---

## Task 3: Route by true size — EXPLAIN bare SQL, max_row_limit band, safety cap, drop 100× block

**Files:**
- Modify: `backend/app/query/pipeline.py` — the EXPLAIN/offload block (current lines 1355-1418), inside `_execute_sql`
- Test: `backend/tests/test_massive_export.py` (update 3 existing pipeline-branch tests + add 2)

- [ ] **Step 1: Update + add the failing tests**

The existing `test_massive_export.py` has a `_run_offload(...)` helper and three pipeline-branch tests written for the OLD behavior (5000 threshold + 100× block). Phase 2 also needs to control `execute_query` (the display path). REPLACE those three tests (`test_offload_delivers_download_url_when_estimate_exceeds_ui_threshold`, `test_offload_failure_asks_user_to_narrow_query`, `test_absurd_estimate_is_blocked_before_export`) and the `_run_offload` helper with this block:

```python
async def _run_routed(estimated_rows: int, export_result: dict | None, rows_returned: list | None = None):
    """Drive _execute_sql past routing. EXPLAIN returns `estimated_rows` for the
    BARE sql; the display path's execute_query returns `rows_returned` (default a
    small list so the display branch returns normally)."""
    from backend.app.query import pipeline

    if rows_returned is None:
        rows_returned = [{"x": 1}]

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": estimated_rows})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=rows_returned)),
        patch("backend.app.worker.tasks.export_massive_query_to_minio", new=AsyncMock(return_value=export_result)),
    ):
        return await pipeline._execute_sql(
            sql="SELECT * FROM orders",
            engine=MagicMock(),
            workspace_id="ws1",
            db=None,
            user_id="u1",
            question="show all orders",
        )


@pytest.mark.asyncio
async def test_estimate_within_display_limit_returns_rows_inline():
    """R̂ ≤ max_row_limit (1000) → display path returns rows, no export."""
    export = AsyncMock()
    from backend.app.query import pipeline

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": 50})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=[{"x": 1}, {"x": 2}])),
        patch("backend.app.worker.tasks.export_massive_query_to_minio", new=export),
    ):
        out = await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=None, user_id="u1", question="q",
        )
    assert out == [{"x": 1}, {"x": 2}]
    export.assert_not_called()


@pytest.mark.asyncio
async def test_estimate_above_display_limit_offloads_with_download_url():
    """R̂ > max_row_limit → export band; the download URL is surfaced."""
    export = {"status": "success", "url": "http://minio/exports/big.csv", "row_count": 50000}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=50_000, export_result=export)
    msg = str(exc.value)
    assert export["url"] in msg
    assert "download" in msg.lower()


@pytest.mark.asyncio
async def test_offload_failure_asks_user_to_narrow_query():
    export = {"status": "error", "url": None, "error": "boom"}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=50_000, export_result=export)
    assert "narrow the query" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_huge_estimate_offloads_instead_of_blocking():
    """Phase 2 removes the >100x hard block: a huge estimate now ROUTES TO EXPORT
    (bounded by max_export_row_limit downstream), it is NOT rejected outright."""
    export = {"status": "success", "url": "http://minio/exports/huge.csv", "row_count": 1_000_000}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=5_000_000, export_result=export)
    m = str(exc.value).lower()
    assert "download" in m
    assert "security exception" not in m  # no longer blocked


@pytest.mark.asyncio
async def test_inline_safety_cap_offloads_when_read_overflows():
    """EXPLAIN underestimates (≤ max_row_limit) but the display read returns
    max_row_limit + 1 rows → switch to export band."""
    over = [{"x": i} for i in range(1001)]  # max_row_limit(1000) + 1
    export = {"status": "success", "url": "http://minio/exports/late.csv", "row_count": 1001}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=200, export_result=export, rows_returned=over)
    assert "download" in str(exc.value).lower()
```

(The earlier worker-contract tests in this file — `test_export_returns_download_url`, `test_export_zero_rows_returns_no_url`, `test_export_failure_is_reported_not_swallowed` — are unchanged; leave them.)

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_massive_export.py -q`
Expected: FAIL — current code blocks the 5M estimate (Security Exception), routes by 5000 not max_row_limit, and never re-routes on inline overflow.

- [ ] **Step 3: Restructure the routing block**

In `backend/app/query/pipeline.py`, REPLACE the block from `try:` (line 1355) through the truncation `if len(result) > row_limit: ... ` clause (ends ~line 1418) with the version below. Keep the outer `try:` and the `except` that follows AFTER this block — only the inner EXPLAIN/offload/execute/truncate logic changes:

```python
    try:
        import uuid

        from backend.app.db import execute_query, explain_query
        from backend.app.worker.tasks import export_massive_query_to_minio

        row_limit = getattr(config, "max_row_limit", 1000)
        export_ceiling = getattr(config, "max_export_row_limit", 100_000)

        # Route on the TRUE size: EXPLAIN the bare (un-limited) SQL. (Phase 2: the
        # display limit is injected only on the display path below, so the estimate
        # reflects the real result size, not the injected cap.)
        explain_res = await explain_query(transformed_sql, config)
        estimated_rows = explain_res.get("estimated_rows", 0)

        async def _offload_to_export():
            # Export band. Bounded by the tenant export ceiling (Phase 3 replaces
            # this with a batched streaming Prefect flow + per_export truncation).
            export_sql = _inject_row_limit(transformed_sql, config.db_type, export_ceiling)
            export_result = await export_massive_query_to_minio(
                sql=export_sql,
                db_config=config,
                conversation_id=str(uuid.uuid4())
                if not workspace_id
                else f"{workspace_id}_{user_id}",
                workspace_id=workspace_id or "default",
            )
            count = export_result.get("row_count", estimated_rows)
            await _audit(success=True, row_count=count, mem_trace=mem_trace)
            if export_result.get("status") == "success" and export_result.get("url"):
                raise ValueError(
                    f"Your query returned ~{count:,} rows — too large to display here. "
                    f"Download the full result (CSV, valid 3 days): {export_result['url']}"
                )
            raise ValueError(
                f"Query estimated ~{estimated_rows:,} rows (too large to display) but the "
                "background export failed — please narrow the query and retry."
            )

        # Estimate exceeds the display ceiling → straight to the export band.
        if estimated_rows > row_limit:
            logger.info(
                "Estimated rows (%d) exceed display limit (%d) → export band.",
                estimated_rows,
                row_limit,
            )
            await _offload_to_export()

        # Display path: cap the read at row_limit + 1 so we can detect an
        # under-estimate. If we actually get row_limit + 1 rows, the true size
        # exceeds the display ceiling → fall through to the export band.
        display_sql = _inject_row_limit(transformed_sql, config.db_type, row_limit)
        result = await execute_query(display_sql, config)

        if len(result) > row_limit:
            logger.info(
                "Inline read overflowed (%d > %d); EXPLAIN under-estimated → export band.",
                len(result),
                row_limit,
            )
            await _offload_to_export()
```

(After this block the function continues with the existing Column-Level Security post-filter at the old line ~1420 — leave that and everything after it unchanged. `result` is now the display result, ≤ `row_limit` rows, exactly as the downstream code expects. The old `explanation += "truncated to ..."` text is intentionally removed: exceeding `row_limit` now routes to export rather than silently truncating the displayed table.)

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_massive_export.py -q`
Expected: PASS (worker-contract tests + the 5 routing tests).

Then the touched-module set to catch nearby regressions:
Run: `cd /Users/tunasonmez/projects/b2metric-aria/backend && uv run pytest tests/test_massive_export.py tests/test_row_limit_injection.py tests/test_llm_sql_prompt.py tests/test_query.py tests/test_sql_visibility.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/pipeline.py backend/tests/test_massive_export.py
git commit -m "feat(backend): route export by true EXPLAIN size + max_row_limit; inline safety cap; drop 100x block"
```

---

## Phase-2 Done Check

- [ ] `uv run pytest tests/test_massive_export.py tests/test_row_limit_injection.py tests/test_llm_sql_prompt.py -q` — green.
- [ ] `uv run pytest tests/ -q` — full backend suite green (the SQL-visibility / query / dashboard suites exercise `_execute_sql`; watch for any test that assumed the old truncate-to-row_limit behavior).
- [ ] **Live (browser, medianova or stc with the export ceiling configured):** ask "show all rows from a large table, no aggregation" → because EXPLAIN now runs on the bare SQL and routes by `max_row_limit`, the answer is the "too large to display — download CSV" message (not a truncated table). Capture via the Playwright bridge.
- [ ] Run `smoke/done-check.sh` and cite evidence.

## Notes / scope boundaries

- The export band still calls the existing in-memory `export_massive_query_to_minio`, now bounded by `max_export_row_limit`. **Phase 3** replaces its internals with the executor `stream_query` + `ArtifactStore.upload_csv_stream` + `export_jobs` + a Prefect `export_query_flow`, and makes delivery async (queued → link).
- **Defensive fallback strip** (spec §B, secondary): if the model still emits a spurious trailing limit despite the Task-1 prompt change AND the user's question has no top-N intent, strip it for the EXPLAIN only. Deferred — the prompt fix is the primary mechanism; add this only if real traffic shows the model disobeying.
- **Carried Phase-1 follow-ups** to fold in alongside Phase 2's test work: integration test for the tenant PATCH DB round-trip; FE client-guard lower bounds (`≥1`); `log.warning` on the limit-only PATCH silent-drop path; helper test for `max_row > 1,000,000`.
