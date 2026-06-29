# Per-User/Team Attribution + Dashboard Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** Make per-user dashboard stats real (not 0) and let an admin filter dashboard activity by team and by user.

**Architecture:** Root cause of the 0s: audit rows store `user_id = NULL` because some identities (e.g. dev `admin`) carry a non-UUID Keycloak `sub`, so `uuid.UUID(sub)` fails in JIT-sync (no `users` row created) and in the audit write. Fix by deriving a **deterministic UUID** from any identity string (UUID passes through; non-UUID → `uuid5`) and using it consistently in JIT-sync, the audit write, and the dashboard read. Then add `team_id` to `data_audit_logs` and populate it, and add `?user_id=`/`?team_id=` filters to `/api/dashboard` with team/user pickers in the UI.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + Postgres (backend); Next.js + React + TS (frontend); pytest.

**Live facts (2026-06-29):** `data_audit_logs` has `customer_id`+`user_id` (no `team_id`); `user_id → users(id)` FK ON DELETE SET NULL. The `admin` user is absent from `users` (non-UUID sub → JIT-sync `uuid.UUID(sub)` raises). All 138 query rows have `user_id NULL`. Historical rows can't be back-attributed (the original identity wasn't recorded) — attribution applies to NEW queries.

---

## Task 1 — Deterministic identity UUID (keystone: makes per-user stats real)

**Files:** Create `backend/app/auth/identity.py`; Modify `backend/app/auth/sync.py`, `backend/app/query/pipeline.py`, `backend/app/api/dashboard.py`; Test `backend/tests/test_identity.py` + update `backend/tests/test_dashboard.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_identity.py`:
```python
import uuid
from backend.app.auth.identity import resolve_identity_uuid

def test_valid_uuid_passes_through():
    u = uuid.uuid4()
    assert resolve_identity_uuid(str(u)) == u

def test_non_uuid_is_deterministic():
    a = resolve_identity_uuid("admin-001")
    b = resolve_identity_uuid("admin-001")
    assert isinstance(a, uuid.UUID) and a == b
    assert resolve_identity_uuid("other") != a

def test_empty_returns_none():
    assert resolve_identity_uuid(None) is None
    assert resolve_identity_uuid("") is None
```

- [ ] **Step 2: Run → fail** (`module not found`): `cd backend && uv run pytest tests/test_identity.py -v`

- [ ] **Step 3: Implement** `backend/app/auth/identity.py`:
```python
"""Deterministic identity → UUID resolution.

Real Keycloak ``sub`` values are UUIDs and pass through unchanged. Legacy/dev
identifiers (e.g. ``admin-001``) are mapped via ``uuid5`` so the SAME identity
always yields the SAME UUID across JIT-sync, audit writes, and dashboard reads —
making per-user attribution consistent instead of dropping to NULL.
"""

import uuid

# Fixed namespace (uuid4, frozen). Do NOT regenerate — changing it re-maps every
# derived identity and breaks attribution continuity.
_IDENTITY_NAMESPACE = uuid.UUID("b1d9f0c2-7a3e-4e2a-9c1b-2f6a8e4d5c30")


def resolve_identity_uuid(identifier: str | None) -> uuid.UUID | None:
    """Map an identity string to a stable UUID, or None when empty."""
    if not identifier:
        return None
    try:
        return uuid.UUID(str(identifier))
    except (ValueError, AttributeError):
        return uuid.uuid5(_IDENTITY_NAMESPACE, str(identifier))
```
Then wire it in:
- `backend/app/auth/sync.py` (~line 70): replace `user_uuid = uuid.UUID(user_ctx.sub)` with `user_uuid = resolve_identity_uuid(user_ctx.sub)` (import it). Keep `external_id=user_ctx.sub`. This creates a `users` row for non-UUID identities so the audit FK resolves.
- `backend/app/query/pipeline.py`: change `_coerce_user_uuid` to delegate to `resolve_identity_uuid` (drop the "non-UUID → None" behavior and its warning; non-UUID now attributes). Keep the `None`-on-empty contract.
- `backend/app/api/dashboard.py` (~line 35): replace `user_uuid = uuid.UUID(str(current_user.user_id))` (in the `try/except`) with `user_uuid = resolve_identity_uuid(str(current_user.user_id))`.

- [ ] **Step 4: Update existing tests** — in `backend/tests/test_dashboard.py`, the `_coerce_user_uuid` tests now reflect new behavior: replace `test_non_uuid_user_id_logs_warning` with a test that `pipeline._coerce_user_uuid("admin-001")` returns a deterministic UUID (== `resolve_identity_uuid("admin-001")`). The workspace test still passes (per-user block now runs against `per_user_session` with empty returns → 0).

- [ ] **Step 5: Run → pass**: `cd backend && uv run pytest tests/test_identity.py tests/test_dashboard.py -v`

- [ ] **Step 6: Commit**: `feat(auth): deterministic identity UUID so audit attributes every user`

**Live check after this task:** log in as `admin`, run ONE chat query, reload dashboard → "Total Queries"/"Queries Today" increment from 0 (new rows now carry the derived `user_id`). Historical rows stay NULL.

---

## Task 2 — `team_id` on audit rows

**Files:** Create migration `backend/alembic/versions/<rev>_add_team_id_to_audit.py`; Modify `backend/app/models/governance.py`, `backend/app/services/audit.py`, `backend/app/query/pipeline.py`; Test `backend/tests/test_dashboard.py`.

- [ ] **Step 1: Migration** — generate with `cd backend && uv run alembic revision -m "add team_id to data_audit_logs"` then fill upgrade/downgrade:
```python
def upgrade() -> None:
    op.add_column("data_audit_logs", sa.Column("team_id", sa.Uuid(), nullable=True))
    op.create_index("ix_data_audit_logs_team_id", "data_audit_logs", ["team_id"])
    op.create_foreign_key(
        "data_audit_logs_team_id_fkey", "data_audit_logs", "teams",
        ["team_id"], ["id"], ondelete="SET NULL",
    )

def downgrade() -> None:
    op.drop_constraint("data_audit_logs_team_id_fkey", "data_audit_logs", type_="foreignkey")
    op.drop_index("ix_data_audit_logs_team_id", table_name="data_audit_logs")
    op.drop_column("data_audit_logs", "team_id")
```
Set `down_revision` to the current head (`cd backend && uv run alembic heads`). Apply: `uv run alembic upgrade head`.

- [ ] **Step 2: Model** — `backend/app/models/governance.py` `DataAuditLog`: add `team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)`.

- [ ] **Step 3: Write-path** — `AuditService.log_event` (`backend/app/services/audit.py`): add `team_id: uuid.UUID | None = None` param and set it on the entry. In `backend/app/query/pipeline.py` `_execute_sql`, resolve a team UUID (`team_uuid = resolve_identity_uuid(team_id)` — `team_id` may be a non-UUID group name) and pass `team_id=team_uuid` in the `audit.log_event(...)` call. Guard the FK: only pass it if a matching `teams` row exists, else leave None (the team may not be provisioned). Simplest safe approach: wrap in try and fall back to None on FK error (the `_audit` already swallows+logs).

- [ ] **Step 4: Test** — extend `test_dashboard.py`: a fake-session test asserting the team-filtered branch (added in Task 3) counts by `team_id`. (If Task 3 not yet built, assert the model/migration round-trips via a lightweight import/attr test.)

- [ ] **Step 5: Run touched tests** (`uv run pytest tests/test_dashboard.py tests/test_audit*.py -v`) **+ migration smoke** (`uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`).

- [ ] **Step 6: Commit**: `feat(audit): record team_id on query audit rows`

---

## Task 3 — Dashboard `?user_id=`/`?team_id=` filters + UI pickers

**Files:** Modify `backend/app/api/dashboard.py`, `backend/tests/test_dashboard.py`; `frontend/src/app/page.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`; possibly a new `frontend/src/components/DashboardFilters.tsx`.

- [ ] **Step 1: Backend filters** — `get_user_dashboard` accepts optional `team_id: str | None = None` and `user_id_filter: str | None = None` query params. When `team_id` is given, the workspace aggregates add `DataAuditLog.team_id == resolve_identity_uuid(team_id)`; when `user_id_filter` is given, add `DataAuditLog.user_id == resolve_identity_uuid(user_id_filter)`. Keep them scoped to the resolved `customer_uuid` (never cross-tenant). Return the same shape; the "Workspace activity" cards now reflect the active filter. Add a `filters` echo block to the response (`{"team_id":..., "user_id":...}`) for the UI.

- [ ] **Step 2: Backend test** — fake-session test: with `team_id="t1"`, assert the workspace query path includes the team filter and returns the seeded count. Write the failing test first.

- [ ] **Step 3: List endpoints for pickers** — reuse existing admin list endpoints if present (`/api/admin/teams`, `/api/admin/users`); otherwise add minimal `GET /api/dashboard/teams` + `/api/dashboard/users` returning `[{id,name}]` scoped to the caller's workspace. Verify which exist first (grep `backend/app/api/endpoints/admin/`).

- [ ] **Step 4: FE filter controls** — `DashboardFilters.tsx`: two dropdowns (Team, User) populated from the list endpoints; on change, call `getDashboard(token, {teamId, userId})`. Wire into `page.tsx` `loadData()` (pass current filter state; refetch on change). Add `getDashboard` params to `api.ts` and a `DashboardFilters` type to `types.ts`. Default = no filter (current behavior).

- [ ] **Step 5: Verify** — `uv run pytest tests/test_dashboard.py -v`; `cd frontend && npm run type-check`; Playwright: log in as admin, pick a team/user, confirm the cards re-scope.

- [ ] **Step 6: Commit**: `feat(dashboard): team/user activity filters`

---

## Verification (whole feature)
- [ ] `cd backend && uv run pytest tests/ -q` (expect all pass; `scripts/test_all.py` is not a pytest module — exclude).
- [ ] `cd frontend && npm run type-check && npm test`
- [ ] Playwright live: admin runs a query → top cards increment; team/user filter re-scopes the cards.

## Notes / decisions
- Historical NULL-user rows are NOT back-filled (original identity unrecoverable). Attribution is forward-looking.
- `_IDENTITY_NAMESPACE` is frozen; never regenerate.
- Filters are always tenant-scoped via `customer_uuid` — never allow cross-customer counts.
