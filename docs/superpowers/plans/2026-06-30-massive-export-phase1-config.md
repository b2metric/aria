# Massive-Export Phase 1 — Config (two thresholds + batch size) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new tenant-scoped config values — `max_export_row_limit` (export ceiling) and `export_batch_size` — alongside the existing `max_row_limit` (display ceiling), persisted on `customer_db_configs`, validated by the invariant `max_row_limit ≤ max_export_row_limit ≤ 1,000,000` and `export_batch_size ≤ max_export_row_limit`, editable in Admin → Tenant Config.

**Architecture:** Two SQLAlchemy columns + Alembic migration with backfill; two `DBConfig` dataclass fields; the admin tenant API (`PATCH`/`GET /admin/tenant`) gains the fields plus a final-state invariant check; the FE tenant-config page gains two inputs with client-side validation. This phase ships independently: an admin can set the two new values and they persist and validate. Nothing yet *consumes* them (routing/export are later phases).

**Tech Stack:** Python 3.14, SQLAlchemy 2 (async, Mapped), Alembic, Pydantic v2, FastAPI, pytest (+ pytest-asyncio), Next.js/React (TS) for the FE.

**Spec:** `docs/superpowers/specs/2026-06-30-massive-query-export-redesign-design.md` (section A).

---

## File Structure

- `backend/app/db/models.py` — `DBConfig` dataclass: add `max_export_row_limit`, `export_batch_size` (defaulted, immutable DTO).
- `backend/app/models/database.py` — `CustomerDBConfig` ORM: add two `mapped_column`s.
- `backend/alembic/versions/<rev>_add_export_limits_to_db_configs.py` — *new* migration (add columns + backfill).
- `backend/app/api/endpoints/admin/tenant.py` — request/response models, defaults, validator, GET + PATCH persistence + invariant guard.
- `backend/tests/test_tenant_export_config.py` — *new* tests for the API models, invariant, and persistence.
- `frontend/src/app/admin/tenant-config/page.tsx` — two new inputs + state + client validation.

**Invariant (single source of truth, reused by tests):**
`1 ≤ max_row_limit ≤ max_export_row_limit ≤ 1_000_000` and `1 ≤ export_batch_size ≤ max_export_row_limit`.

**Defaults:** `max_row_limit=1000` (unchanged), `max_export_row_limit=100000`, `export_batch_size=50000`.

---

## Task 1: Extend the `DBConfig` DTO

**Files:**
- Modify: `backend/app/db/models.py` (the `DBConfig` dataclass, ends at `max_row_limit: int = 1000`)
- Test: `backend/tests/test_tenant_export_config.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_tenant_export_config.py`:

```python
"""Phase 1 — two-threshold export config (DBConfig DTO + admin API + invariant)."""

from __future__ import annotations

import pytest

from backend.app.db.models import DBConfig, DatabaseType


def test_dbconfig_has_export_fields_with_defaults():
    cfg = DBConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="h",
        port=5432,
        database="d",
        username="u",
        password="p",
    )
    # display ceiling unchanged
    assert cfg.max_row_limit == 1000
    # new export ceiling + batch size defaults
    assert cfg.max_export_row_limit == 100_000
    assert cfg.export_batch_size == 50_000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tenant_export_config.py::test_dbconfig_has_export_fields_with_defaults -q`
Expected: FAIL with `AttributeError: 'DBConfig' object has no attribute 'max_export_row_limit'`.

- [ ] **Step 3: Add the fields**

In `backend/app/db/models.py`, in the `DBConfig` dataclass, immediately after the line `max_row_limit: int = 1000`, add:

```python
    max_export_row_limit: int = 100_000
    export_batch_size: int = 50_000
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tenant_export_config.py::test_dbconfig_has_export_fields_with_defaults -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/tests/test_tenant_export_config.py
git commit -m "feat(backend): add export-limit fields to DBConfig DTO"
```

---

## Task 2: Add the ORM columns

**Files:**
- Modify: `backend/app/models/database.py:56-61` (`CustomerDBConfig.max_row_limit` block)

- [ ] **Step 1: Add the two columns**

In `backend/app/models/database.py`, immediately after the `max_row_limit` `mapped_column(...)` block (it ends at the line with `comment="Hard limit for rows returned per query",` then `)`), insert:

```python
    max_export_row_limit: Mapped[int] = mapped_column(
        Integer,
        default=100_000,
        server_default="100000",
        comment="Max rows written to a CSV export artifact (export ceiling)",
    )
    export_batch_size: Mapped[int] = mapped_column(
        Integer,
        default=50_000,
        server_default="50000",
        comment="Rows fetched per batch when streaming an export",
    )
```

- [ ] **Step 2: Verify the model imports cleanly**

Run: `uv run python -c "from backend.app.models.database import CustomerDBConfig; print(CustomerDBConfig.__table__.c.keys())"`
Expected: the printed column list includes `max_export_row_limit` and `export_batch_size`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/database.py
git commit -m "feat(backend): add export-limit columns to CustomerDBConfig ORM"
```

---

## Task 3: Alembic migration (add columns + backfill)

**Files:**
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_export_limits_to_db_configs.py`

Current head is `b163496fb992` (verified via `alembic heads`).

- [ ] **Step 1: Create the migration file**

Create `backend/alembic/versions/a1b2c3d4e5f6_add_export_limits_to_db_configs.py`:

```python
"""add export-limit columns to customer_db_configs

Revision ID: a1b2c3d4e5f6
Revises: b163496fb992
Create Date: 2026-06-30

Adds max_export_row_limit (export ceiling) and export_batch_size (streaming
batch size). Backfills export ceiling from the existing display limit so no
tenant's export cap is below its current query cap.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "b163496fb992"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_db_configs",
        sa.Column(
            "max_export_row_limit",
            sa.Integer(),
            nullable=False,
            server_default="100000",
        ),
    )
    op.add_column(
        "customer_db_configs",
        sa.Column(
            "export_batch_size",
            sa.Integer(),
            nullable=False,
            server_default="50000",
        ),
    )
    # Backfill: export ceiling never below the existing display ceiling.
    op.execute(
        "UPDATE customer_db_configs "
        "SET max_export_row_limit = GREATEST(max_row_limit, 100000)"
    )


def downgrade() -> None:
    op.drop_column("customer_db_configs", "export_batch_size")
    op.drop_column("customer_db_configs", "max_export_row_limit")
```

- [ ] **Step 2: Apply the migration against the dev DB**

Run: `docker exec aria-backend alembic upgrade head`
Expected: output ends with `Running upgrade b163496fb992 -> a1b2c3d4e5f6`.

- [ ] **Step 3: Verify the columns + backfill**

Run:
```bash
docker exec aria-postgres psql -U aria -d aria -c \
"SELECT column_name, column_default FROM information_schema.columns \
 WHERE table_name='customer_db_configs' AND column_name IN ('max_export_row_limit','export_batch_size');"
```
Expected: two rows, defaults `100000` and `50000`.

Run:
```bash
docker exec aria-postgres psql -U aria -d aria -c \
"SELECT max_row_limit, max_export_row_limit, export_batch_size FROM customer_db_configs;"
```
Expected: every row has `max_export_row_limit = GREATEST(max_row_limit, 100000)` and `export_batch_size = 50000`.

- [ ] **Step 4: Verify downgrade reverts (then re-upgrade)**

Run: `docker exec aria-backend alembic downgrade -1 && docker exec aria-backend alembic upgrade head`
Expected: downgrade drops the columns without error, upgrade re-adds them.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/a1b2c3d4e5f6_add_export_limits_to_db_configs.py
git commit -m "feat(backend): migration — export-limit columns + backfill on customer_db_configs"
```

---

## Task 4: Admin API request/response models + invariant validator

**Files:**
- Modify: `backend/app/api/endpoints/admin/tenant.py` (constants `23-24`, `TenantConfigUpdate` `39-59`, `TenantConfigResponse` `62-69`)
- Test: `backend/tests/test_tenant_export_config.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_tenant_export_config.py`:

```python
from pydantic import ValidationError

from backend.app.api.endpoints.admin.tenant import TenantConfigUpdate


def test_update_accepts_new_fields():
    body = TenantConfigUpdate(
        max_row_limit=1000, max_export_row_limit=200_000, export_batch_size=20_000
    )
    assert body.max_export_row_limit == 200_000
    assert body.export_batch_size == 20_000


def test_update_rejects_export_below_query_when_both_present():
    with pytest.raises(ValidationError):
        TenantConfigUpdate(max_row_limit=50_000, max_export_row_limit=10_000)


def test_update_rejects_batch_above_export_when_both_present():
    with pytest.raises(ValidationError):
        TenantConfigUpdate(max_export_row_limit=10_000, export_batch_size=20_000)


def test_update_allows_partial_single_field():
    # only one of the related fields → no cross-field error at request level
    body = TenantConfigUpdate(export_batch_size=5_000)
    assert body.export_batch_size == 5_000


def test_query_limit_has_no_lower_floor():
    # the previous ge=100 floor is removed
    body = TenantConfigUpdate(max_row_limit=1)
    assert body.max_row_limit == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tenant_export_config.py -q -k "update or floor"`
Expected: FAIL — `TypeError`/`ValidationError` because the fields don't exist yet (and `max_row_limit=1` currently rejected by `ge=100`).

- [ ] **Step 3: Update the constants + models**

In `backend/app/api/endpoints/admin/tenant.py`:

3a. After the existing `DEFAULT_MAX_ROW_LIMIT = 1000` (line 24), add:

```python
DEFAULT_MAX_EXPORT_ROW_LIMIT = 100000
DEFAULT_EXPORT_BATCH_SIZE = 50000
HARD_ROW_CEILING = 1_000_000
```

3b. Add `model_validator` to the imports — change `from pydantic import BaseModel, Field` to:

```python
from pydantic import BaseModel, Field, model_validator
```

3c. Replace the `max_row_limit` field in `TenantConfigUpdate` (lines 48-53) — remove the `ge=100` floor — and add the two new fields plus a cross-field validator. The `TenantConfigUpdate` class body becomes:

```python
class TenantConfigUpdate(BaseModel):
    """Update tenant configuration."""

    daily_token_limit: int | None = Field(
        default=None,
        ge=1000,
        le=10_000_000,
        description="Daily token limit per user/team (1K - 10M)",
    )
    max_row_limit: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description="Max rows rendered per query in the UI (display ceiling)",
    )
    max_export_row_limit: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description="Max rows written to a CSV export artifact (export ceiling)",
    )
    export_batch_size: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description="Rows fetched per batch when streaming an export",
    )
    db_config: DBConfigModel | None = None
    language: str | None = Field(
        default=None,
        pattern="^(en|tr)$",
        description="Customer response language: 'en' or 'tr' (forces all chat/insight/suggestions)",
    )

    @model_validator(mode="after")
    def _check_ordering(self) -> "TenantConfigUpdate":
        # Only validate the relationship between fields submitted together;
        # the handler does the final check against stored values.
        if (
            self.max_row_limit is not None
            and self.max_export_row_limit is not None
            and self.max_row_limit > self.max_export_row_limit
        ):
            raise ValueError("max_row_limit must be ≤ max_export_row_limit")
        if (
            self.export_batch_size is not None
            and self.max_export_row_limit is not None
            and self.export_batch_size > self.max_export_row_limit
        ):
            raise ValueError("export_batch_size must be ≤ max_export_row_limit")
        return self
```

3d. Add the two fields to `TenantConfigResponse` (after `max_row_limit: int`):

```python
    max_export_row_limit: int
    export_batch_size: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tenant_export_config.py -q -k "update or floor"`
Expected: PASS (all 5).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/admin/tenant.py backend/tests/test_tenant_export_config.py
git commit -m "feat(backend): tenant API gains export-limit fields + ordering validator (drop max_row_limit floor)"
```

---

## Task 5: GET returns the new fields

**Files:**
- Modify: `backend/app/api/endpoints/admin/tenant.py` GET handler (the `row_limit` init above the `try`, the read block `114-116`, the response `121-137`)

- [ ] **Step 1: Add a default-initialized read + response fields**

5a. Find where `row_limit` is initialized for the GET handler (a `row_limit = DEFAULT_MAX_ROW_LIMIT`-style line above the `try`). Next to it, initialize:

```python
    export_row_limit = DEFAULT_MAX_EXPORT_ROW_LIMIT
    export_batch = DEFAULT_EXPORT_BATCH_SIZE
```

5b. In the read block (currently lines 114-116), extend:

```python
                # Also fetch row/export limits if they exist
                if db_config_res:
                    row_limit = db_config_res.max_row_limit
                    export_row_limit = db_config_res.max_export_row_limit
                    export_batch = db_config_res.export_batch_size
```

5c. In the `return TenantConfigResponse(...)` (lines 121-137), add the two fields:

```python
        max_export_row_limit=export_row_limit,
        export_batch_size=export_batch,
```

- [ ] **Step 2: Verify the response model is satisfied**

Run: `uv run python -c "from backend.app.api.endpoints.admin.tenant import TenantConfigResponse; TenantConfigResponse(daily_token_limit=1, max_row_limit=1, max_export_row_limit=2, export_batch_size=1, source='default'); print('ok')"`
Expected: prints `ok` (no validation error for the new required fields).

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/endpoints/admin/tenant.py
git commit -m "feat(backend): tenant GET returns export-limit fields"
```

---

## Task 6: PATCH persists the new fields + final-state invariant guard

**Files:**
- Modify: `backend/app/api/endpoints/admin/tenant.py` PATCH handler (the "at least one field" guard `152-161`, the db_config update branch `229-257`, the standalone `elif body.max_row_limit is not None:` branch at `259`)
- Test: `backend/tests/test_tenant_export_config.py`

- [ ] **Step 1: Write the failing test (final-state invariant helper)**

The handler needs a pure helper so we can unit-test the invariant without a DB. Append to `backend/tests/test_tenant_export_config.py`:

```python
from backend.app.api.endpoints.admin.tenant import validate_row_limit_invariant


def test_invariant_helper_accepts_valid_combo():
    # display ≤ export ≤ 1M and batch ≤ export
    validate_row_limit_invariant(max_row=1000, max_export=100_000, batch=50_000)  # no raise


def test_invariant_helper_rejects_export_below_display():
    with pytest.raises(ValueError):
        validate_row_limit_invariant(max_row=200_000, max_export=100_000, batch=50_000)


def test_invariant_helper_rejects_batch_above_export():
    with pytest.raises(ValueError):
        validate_row_limit_invariant(max_row=1000, max_export=100_000, batch=200_000)


def test_invariant_helper_rejects_above_hard_ceiling():
    with pytest.raises(ValueError):
        validate_row_limit_invariant(max_row=1000, max_export=2_000_000, batch=50_000)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_tenant_export_config.py -q -k invariant_helper`
Expected: FAIL — `ImportError: cannot import name 'validate_row_limit_invariant'`.

- [ ] **Step 3: Add the helper + wire persistence**

3a. Add the pure helper near the constants in `tenant.py`:

```python
def validate_row_limit_invariant(*, max_row: int, max_export: int, batch: int) -> None:
    """Enforce 1 ≤ max_row ≤ max_export ≤ HARD_ROW_CEILING and batch ≤ max_export."""
    if not (1 <= max_row <= max_export <= HARD_ROW_CEILING):
        raise ValueError(
            "Require 1 ≤ max_row_limit ≤ max_export_row_limit ≤ 1,000,000 "
            f"(got max_row_limit={max_row}, max_export_row_limit={max_export})"
        )
    if not (1 <= batch <= max_export):
        raise ValueError(
            "Require 1 ≤ export_batch_size ≤ max_export_row_limit "
            f"(got export_batch_size={batch}, max_export_row_limit={max_export})"
        )
```

3b. In the db_config update branch, after the existing `if body.max_row_limit is not None: db_config_res.max_row_limit = body.max_row_limit` (lines 235-236), add:

```python
                    if body.max_export_row_limit is not None:
                        db_config_res.max_export_row_limit = body.max_export_row_limit
                    if body.export_batch_size is not None:
                        db_config_res.export_batch_size = body.export_batch_size
```

3c. In the `CustomerDBConfig(...)` constructor for the create path (lines 242-257), add after `max_row_limit=body.max_row_limit or DEFAULT_MAX_ROW_LIMIT,`:

```python
                        max_export_row_limit=body.max_export_row_limit
                        or DEFAULT_MAX_EXPORT_ROW_LIMIT,
                        export_batch_size=body.export_batch_size
                        or DEFAULT_EXPORT_BATCH_SIZE,
```

3d. Extend the standalone `elif body.max_row_limit is not None:` branch (line 259) so it ALSO triggers when only the export fields are sent, and persists each provided field. Replace that `elif` condition with:

```python
            elif (
                body.max_row_limit is not None
                or body.max_export_row_limit is not None
                or body.export_batch_size is not None
            ):
```

and inside it, after the existing code loads `db_config_res` for the customer, set each provided field (mirror 3b): `db_config_res.max_row_limit`, `.max_export_row_limit`, `.export_batch_size` from `body` where not None. (Read the existing branch body first; keep its customer-load + 404 handling, only add the field assignments.)

3e. After all fields are applied but BEFORE `await session.commit()`, when `db_config_res` is not None, enforce the final-state invariant and convert failures to HTTP 400:

```python
            if db_config_res is not None:
                try:
                    validate_row_limit_invariant(
                        max_row=db_config_res.max_row_limit,
                        max_export=db_config_res.max_export_row_limit,
                        batch=db_config_res.export_batch_size,
                    )
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e)) from e
```

3f. Update the "at least one field" guard (lines 152-161) to include the new fields:

```python
    if (
        body.daily_token_limit is None
        and body.max_row_limit is None
        and body.max_export_row_limit is None
        and body.export_batch_size is None
        and body.db_config is None
        and body.language is None
    ):
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_tenant_export_config.py -q`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/admin/tenant.py backend/tests/test_tenant_export_config.py
git commit -m "feat(backend): persist + invariant-guard export limits in tenant PATCH"
```

---

## Task 7: FE — two new inputs in Tenant Config

**Files:**
- Modify: `frontend/src/app/admin/tenant-config/page.tsx` (interface `~20`, load `~56`, save body `~87`, the `max_row_limit` input block `~199-221`)

- [ ] **Step 1: Extend the TS interface + state**

7a. In the config interface (around line 20, `max_row_limit: number;`), add:

```ts
  max_export_row_limit: number;
  export_batch_size: number;
```

7b. Add React state near the existing `rowLimit` state:

```ts
  const [exportRowLimit, setExportRowLimit] = useState<number>(100000);
  const [exportBatchSize, setExportBatchSize] = useState<number>(50000);
```

7c. In the load effect (around line 56, `setRowLimit(data.max_row_limit);`), add:

```ts
        setExportRowLimit(data.max_export_row_limit);
        setExportBatchSize(data.export_batch_size);
```

7d. In the save payload (around line 87, `max_row_limit: rowLimit,`), add:

```ts
        max_export_row_limit: exportRowLimit,
        export_batch_size: exportBatchSize,
```

- [ ] **Step 2: Add the two inputs + update the display-limit helper text**

After the existing `max_row_limit` input block (the `<input>` + helper text ending with "Range: 100 - 1,000,000", ~line 221), add two inputs, and change the existing display-limit helper text to drop the "100" floor (e.g. "Range: 1 - 1,000,000"). Insert:

```tsx
              <div className="mt-4">
                <label className="block text-sm font-medium mb-1">
                  Max Rows per Export (CSV)
                </label>
                <input
                  type="number"
                  min={1}
                  max={1000000}
                  value={exportRowLimit}
                  onChange={(e) => setExportRowLimit(Number(e.target.value))}
                  className="w-full rounded-md border px-3 py-2"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Results above the per-query limit are exported as a CSV up to this many
                  rows. Must be ≥ Max Rows per Query and ≤ 1,000,000.
                </p>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium mb-1">Export Batch Size</label>
                <input
                  type="number"
                  min={1}
                  max={1000000}
                  value={exportBatchSize}
                  onChange={(e) => setExportBatchSize(Number(e.target.value))}
                  className="w-full rounded-md border px-3 py-2"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Rows fetched per batch while streaming an export. Must be ≤ Max Rows per
                  Export.
                </p>
              </div>
```

(If the file uses a design-system `Input`/`Label` component, match that pattern instead of the raw `<input>`/`<label>` + Tailwind classes above — follow the file's established markup.)

- [ ] **Step 3: Guard save with the invariant (client-side)**

In the save handler, before issuing the PATCH, add:

```ts
    if (!(rowLimit <= exportRowLimit && exportRowLimit <= 1000000)) {
      setError("Max Rows per Query must be ≤ Max Rows per Export ≤ 1,000,000");
      return;
    }
    if (!(exportBatchSize <= exportRowLimit)) {
      setError("Export Batch Size must be ≤ Max Rows per Export");
      return;
    }
```

(Use whatever error surface the file already has — `setError`, a toast, etc.)

- [ ] **Step 4: Type-check + visual verify**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new type errors.

Then render `http://aria.localhost/admin/tenant-config` (Playwright/Chrome MCP, logged in as admin) and screenshot: the two new inputs appear, load current values, and saving an invalid combo (export < query) surfaces the client error.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/admin/tenant-config/page.tsx
git commit -m "feat(frontend): tenant-config inputs for export row limit + batch size"
```

---

## Phase-1 Done Check

- [ ] `uv run pytest tests/test_tenant_export_config.py -q` — all green.
- [ ] `uv run pytest tests/ -q` — full backend suite still green (no regressions).
- [ ] `alembic upgrade head` applied; columns present + backfilled on the dev DB.
- [ ] `http://aria.localhost/admin/tenant-config` shows + saves the two new fields; invalid combos rejected both client- and server-side.
- [ ] Run `smoke/done-check.sh` (BE + FE + tests + boot/login) and cite evidence.

## Notes for later phases (NOT this plan)

- **Phase 2** (routing): remove the `llm_sql.py` auto-limit prompt rule; run EXPLAIN on the bare SQL before limit injection; route by `R̂` vs `max_row_limit`; inline safety cap; drop the `100×` hard block.
- **Phase 3** (streaming export): executor `stream_query`; `ArtifactStore.upload_csv_stream`; `export_jobs` table; Prefect `export_query_flow`; dispatch from the pipeline.
- **Phase 4** (delivery/FE): `/api/exports` list/status/download-proxy; inline chat export status + download; `/exports` page.
