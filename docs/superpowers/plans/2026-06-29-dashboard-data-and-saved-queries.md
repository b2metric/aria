# Dashboard Data + Saved Queries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the dashboard show real activity (it reads 0 today) and finish the half-wired Saved Queries feature end-to-end.

**Architecture:** The dashboard currently counts `data_audit_logs`/`token_usage_daily` rows filtered by `user_id`. In this environment the JWT `sub` is a non-UUID identifier (legacy `admin-001`/`unknown-user` fallback — see `backend/app/auth/rbac.py:80-82`), so `uuid.UUID(sub)` raises and the per-user filter matches nothing → every stat is 0. The 138 real query rows carry a valid `customer_id` but `user_id` NULL. We (1) add **workspace-scoped** stats (counted by `customer_id`, always populated) alongside the existing per-user stats, (2) stop the **silent** user-id drop in the audit write so misconfigured identities are visible in logs, and (3) wire **Saved Queries** fully: a Save action in chat, the dashboard fetching the real list, and unifying the two divergent `SavedQuery` types.

**Tech Stack:** FastAPI + SQLAlchemy async + Postgres + Redis (backend); Next.js (App Router) + React + TypeScript + Tailwind (frontend); pytest (backend tests); Playwright (smoke).

**Root-cause evidence (from live DB, 2026-06-29):**
- `data_audit_logs` action=query: 138 rows → 134 `user_id` NULL (13–29 Jun, incl. today), 4 attributed to one Keycloak-UUID user. `customer_id` populated on all.
- `token_usage_daily`: 2 rows, both `2026-06-15` (today is 06-29; the card filters `usage_date == today`).
- `users.id = uuid.UUID(sub)` (`backend/app/auth/sync.py:70`) → non-UUID sub never gets a row and never matches.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `backend/app/api/dashboard.py` | `GET /api/dashboard` — add workspace-scoped stats + workspace 7-day trend; keep per-user stats | Modify |
| `backend/app/query/pipeline.py` | `_execute_sql` audit helper — warn (not silently drop) on non-UUID user_id | Modify (`1141-1143`) |
| `backend/tests/test_dashboard.py` | Tests for per-user + workspace stats and non-UUID identity fallback | Create |
| `frontend/src/lib/types.ts` | Unify `SavedQuery` to API shape; add `workspaceStats` to `DashboardData` | Modify |
| `frontend/src/lib/api.ts` | Remove duplicate `SavedQuery`; import from types | Modify (`378-386`) |
| `frontend/src/components/SavedQueries.tsx` | Render API shape (`name`/`question`/`created_at`); add delete + empty state | Modify |
| `frontend/src/app/page.tsx` | Fetch real saved-queries list; render `workspaceStats` row | Modify |
| `frontend/src/app/chat/page.tsx` | Add a "Save query" action next to View SQL | Modify (`739-749`) |

---

## Task 1: Backend — workspace-scoped dashboard stats

**Files:**
- Modify: `backend/app/api/dashboard.py`
- Test: `backend/tests/test_dashboard.py`

The new response keeps `stats` (per-user) and adds `workspaceStats` (per-customer, always populated). The 7-day `chartData` becomes the **workspace** trend (where the data actually is). Workspace counts use `customer_id` resolved from `workspace_id` slug, mirroring `pipeline.py:1131-1137`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_dashboard.py`. Mirror the fixture style already used in `backend/tests/test_admin_metrics.py` (same `DataAuditLog`/`customers` setup) — open that file first and reuse its app/client + seeded-session fixtures. The test seeds one customer (slug `acme`), 3 `data_audit_logs` action=`query` rows for that customer with `user_id=NULL`, authenticates as a **non-UUID** identity (`sub="admin-001"`, `workspace_id="acme"`), and asserts the workspace card reflects the 3 rows even though the per-user card is 0.

```python
import pytest

@pytest.mark.asyncio
async def test_workspace_stats_count_customer_rows_when_user_is_non_uuid(
    dashboard_client, seed_customer_query_rows
):
    # seed_customer_query_rows: customer slug "acme" + 3 action="query" audit rows, user_id NULL
    resp = await dashboard_client.get(
        "/api/dashboard",
        headers={"Authorization": "Bearer admin-001"},  # non-UUID sub
        params={"workspace_id": "acme"},
    )
    assert resp.status_code == 200
    body = resp.json()

    ws = {s["label"]: s["value"] for s in body["workspaceStats"]}
    assert ws["Workspace Queries"] == "3"

    personal = {s["label"]: s["value"] for s in body["stats"]}
    assert personal["Total Queries"] == "0"  # per-user unchanged (non-UUID → 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.dev.yml exec -T backend pytest backend/tests/test_dashboard.py -v`
Expected: FAIL — `workspaceStats` key missing (`KeyError`).

- [ ] **Step 3: Implement workspace stats in `dashboard.py`**

In `backend/app/api/dashboard.py`, after the per-user block (current line 93, end of the 7-day loop) and before the saved-queries block, add customer resolution + workspace aggregates. Replace the `chartData` source with the workspace trend.

```python
    # ── Resolve customer (workspace) for workspace-scoped stats ──────────
    # customer_id is populated on every audit row even when user_id is NULL
    # (non-UUID identities), so workspace counts surface real activity that
    # the per-user counts above cannot.
    from sqlalchemy import text as _text
    from backend.app.models.governance import DataAuditLog as _DAL

    ws_total = 0
    ws_today = 0
    ws_tokens_today = 0
    ws_active_users = 0
    ws_trend: list[dict] = []
    customer_uuid = None
    try:
        async with sessionmaker() as session:
            row = (
                await session.execute(
                    _text("SELECT id FROM customers WHERE slug = :slug"),
                    {"slug": workspace_id},
                )
            ).fetchone()
            if row:
                customer_uuid = row[0]

            if customer_uuid is not None:
                ws_total = (
                    await session.scalar(
                        select(func.count(_DAL.id)).where(
                            _DAL.customer_id == customer_uuid, _DAL.action == "query"
                        )
                    )
                ) or 0
                ws_today = (
                    await session.scalar(
                        select(func.count(_DAL.id)).where(
                            _DAL.customer_id == customer_uuid,
                            _DAL.action == "query",
                            _DAL.created_at >= today,
                        )
                    )
                ) or 0
                ws_tokens_today = (
                    await session.scalar(
                        select(func.sum(TokenUsageDaily.tokens_used)).where(
                            TokenUsageDaily.customer_id == customer_uuid,
                            TokenUsageDaily.usage_date == today.date(),
                        )
                    )
                ) or 0
                ws_active_users = (
                    await session.scalar(
                        select(func.count(func.distinct(_DAL.user_id))).where(
                            _DAL.customer_id == customer_uuid,
                            _DAL.action == "query",
                            _DAL.created_at >= today - timedelta(days=7),
                            _DAL.user_id.is_not(None),
                        )
                    )
                ) or 0

                for i in range(6, -1, -1):
                    day = today - timedelta(days=i)
                    next_day = day + timedelta(days=1)
                    day_queries = (
                        await session.scalar(
                            select(func.count(_DAL.id)).where(
                                _DAL.customer_id == customer_uuid,
                                _DAL.action == "query",
                                _DAL.created_at >= day,
                                _DAL.created_at < next_day,
                            )
                        )
                    ) or 0
                    ws_trend.append({"date": day.strftime("%b %d"), "queries": day_queries})
    except Exception as exc:
        log.warning("Workspace dashboard fetch failed: %s", exc)
```

Confirm `TokenUsageDaily` has a `customer_id` column before using it (grep `backend/app/models/token.py`); if it does not, drop the `ws_tokens_today` customer filter to a `user_id.is_not(None)` aggregate or omit that card — do **not** invent a column.

Then add the `workspaceStats` list and switch the chart to the workspace trend in the return value:

```python
    workspace_stats = [
        {"label": "Workspace Queries", "value": str(ws_total), "icon": "Database"},
        {"label": "Queries Today", "value": str(ws_today), "change": "Workspace", "changeType": "neutral", "icon": "Activity"},
        {"label": "Tokens Today", "value": f"{ws_tokens_today:,}", "icon": "Zap"},
        {"label": "Active Users (7d)", "value": str(ws_active_users), "icon": "Users"},
    ]
```

In the final `return {...}`, set `"chartData": ws_trend or recent_trend` and add `"workspaceStats": workspace_stats,`. Keep `"savedQueries": []` for now (Task 6 makes the FE fetch the real list).

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.dev.yml exec -T backend pytest backend/tests/test_dashboard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/dashboard.py backend/tests/test_dashboard.py
git commit -m "feat(dashboard): add workspace-scoped stats so real query activity surfaces"
```

---

## Task 2: Backend — stop the silent user-id drop in audit write

**Files:**
- Modify: `backend/app/query/pipeline.py:1141-1143`
- Test: `backend/tests/test_dashboard.py`

Today a non-UUID `user_id` is swallowed by `contextlib.suppress(ValueError, AttributeError)`, leaving `_user_uuid=None` with no trace. Log a warning so misconfigured identities are diagnosable; behaviour for valid UUIDs is unchanged.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_dashboard.py`:

```python
import logging
from backend.app.query import pipeline

def test_non_uuid_user_id_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger=pipeline.logger.name):
        result = pipeline._coerce_user_uuid("admin-001")
    assert result is None
    assert any("non-UUID user_id" in r.message for r in caplog.records)

def test_valid_uuid_user_id_coerces():
    import uuid
    u = uuid.uuid4()
    assert pipeline._coerce_user_uuid(str(u)) == u
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.dev.yml exec -T backend pytest backend/tests/test_dashboard.py -k coerce -v`
Expected: FAIL — `pipeline._coerce_user_uuid` does not exist (`AttributeError`).

- [ ] **Step 3: Implement the helper and use it**

In `backend/app/query/pipeline.py`, add near the top-level helpers (module scope):

```python
def _coerce_user_uuid(user_id: str | None) -> _uuid.UUID | None:
    """Parse a user identifier to UUID; warn (don't silently drop) on non-UUID.

    In some environments the JWT ``sub`` is a non-UUID legacy identifier
    (e.g. ``admin-001``). Such audit rows cannot be attributed to a user and
    will never appear on the per-user dashboard — log so it is diagnosable.
    """
    if not user_id:
        return None
    try:
        return _uuid.UUID(user_id)
    except (ValueError, AttributeError):
        logger.warning("Audit: non-UUID user_id %r — row will be unattributed", user_id)
        return None
```

Replace the inline parse at `pipeline.py:1141-1143`:

```python
    _user_uuid = _coerce_user_uuid(user_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.dev.yml exec -T backend pytest backend/tests/test_dashboard.py -k coerce -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/query/pipeline.py backend/tests/test_dashboard.py
git commit -m "fix(audit): warn instead of silently dropping non-UUID user_id"
```

---

## Task 3: Frontend — unify the `SavedQuery` type

**Files:**
- Modify: `frontend/src/lib/types.ts:18-25`, `frontend/src/lib/types.ts:31-37`
- Modify: `frontend/src/lib/api.ts:380-386`

There are two divergent `SavedQuery` types (UI: `query`/`createdAt`/`tags`; API: `question`/`sql`/`created_at`). Unify on the API shape (the backend's real contract) and add `workspaceStats` to `DashboardData`.

- [ ] **Step 1: Update `types.ts`**

Replace the `SavedQuery` interface (lines 18-25) with the API shape:

```typescript
export interface SavedQuery {
  id: string;
  name: string;
  question: string;
  sql: string;
  created_at: string;
}
```

In `DashboardData` (lines 31-37) add `workspaceStats`:

```typescript
export interface DashboardData {
  stats: StatCardData[];
  workspaceStats: StatCardData[];
  recentConversations: Conversation[];
  savedQueries: SavedQuery[];
  chartData: ChartDataPoint[];
  chartConfig: ChartConfig;
}
```

- [ ] **Step 2: De-duplicate in `api.ts`**

In `frontend/src/lib/api.ts` remove the local `SavedQuery` interface (lines 380-386) and import the unified type. Add (or extend an existing) `@/lib/types` import with `SavedQuery`:

```typescript
import type { SavedQuery } from "@/lib/types";
```

Keep the `saveQuery`/`listSavedQueries`/`deleteSavedQuery` functions — only the duplicate interface is removed.

- [ ] **Step 3: Type-check**

Run: `docker compose -f docker-compose.dev.yml exec -T frontend npx tsc --noEmit`
Expected: errors ONLY in `SavedQueries.tsx` / `page.tsx` (fixed in Tasks 4–6); no error originating in `types.ts` or `api.ts`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "refactor(types): unify SavedQuery on API shape; add workspaceStats"
```

---

## Task 4: Frontend — `SavedQueries.tsx` renders the API shape + delete

**Files:**
- Modify: `frontend/src/components/SavedQueries.tsx`

- [ ] **Step 1: Rewrite the component**

Replace the file with one that renders `name`/`question`/`created_at`, shows an empty state, and supports delete:

```tsx
import type { SavedQuery } from "@/lib/types";

interface SavedQueriesProps {
  queries: SavedQuery[];
  onSelect: (query: SavedQuery) => void;
  onDelete?: (id: string) => void;
}

export default function SavedQueries({ queries, onSelect, onDelete }: SavedQueriesProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Saved Queries</h3>
        <span className="text-xs text-gray-400">{queries.length} saved</span>
      </div>
      <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
        {queries.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-gray-400">
            No saved queries yet. Save one from a chat answer to see it here.
          </p>
        )}
        {queries.map((q) => (
          <div key={q.id} className="flex items-start gap-2 px-5 py-3 hover:bg-gray-50 transition-colors group">
            <button onClick={() => onSelect(q)} className="flex-1 min-w-0 text-left">
              <p className="text-sm font-medium text-gray-800 truncate group-hover:text-blue-600 transition-colors">
                {q.name}
              </p>
              <p className="text-xs text-gray-400 truncate mt-0.5">{q.question}</p>
            </button>
            <span className="text-[10px] text-gray-400 whitespace-nowrap pt-0.5">
              {new Date(q.created_at).toLocaleDateString()}
            </span>
            {onDelete && (
              <button
                onClick={() => onDelete(q.id)}
                aria-label="Delete saved query"
                className="text-gray-300 hover:text-red-500 text-xs px-1"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `docker compose -f docker-compose.dev.yml exec -T frontend npx tsc --noEmit`
Expected: no errors in `SavedQueries.tsx` (remaining errors only in `page.tsx`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SavedQueries.tsx
git commit -m "feat(saved-queries): render API shape with empty state and delete"
```

---

## Task 5: Frontend — chat "Save query" action

**Files:**
- Modify: `frontend/src/app/chat/page.tsx` (import at line 5; SQL block at 739-749)

- [ ] **Step 1: Import `saveQuery`**

Extend the existing `@/lib/api` import (line 5) to include `saveQuery`:

```tsx
import { streamQuery, streamResume, getRunStatus, fetchConversations, fetchConversation, deleteConversation, fetchWorkspaceSuggestions, saveQuery } from "@/lib/api";
```

- [ ] **Step 2: Add a Save button in the SQL block**

The originating question for an assistant message is the nearest preceding `role === "user"` message. Replace the `msg.sql && (...)` block (lines 740-749) with one that adds a Save button using `token` (already in scope at line 124) and the derived question:

```tsx
                {msg.sql && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-medium text-gray-500 hover:text-gray-700 select-none">
                      🔍 View SQL
                    </summary>
                    <pre className="mt-1 text-xs bg-gray-900 text-green-400 p-3 rounded-lg overflow-auto font-mono leading-relaxed">
                      {msg.sql}
                    </pre>
                    <button
                      onClick={async () => {
                        const idx = messages.findIndex((m) => m.id === msg.id);
                        const q =
                          [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")?.content ?? "";
                        try {
                          await saveQuery(q, msg.sql!, undefined, token);
                          alert("Query saved");
                        } catch {
                          alert("Could not save query");
                        }
                      }}
                      className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-blue-600"
                    >
                      💾 Save query
                    </button>
                  </details>
                )}
```

- [ ] **Step 3: Type-check**

Run: `docker compose -f docker-compose.dev.yml exec -T frontend npx tsc --noEmit`
Expected: no new errors from `chat/page.tsx`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/chat/page.tsx
git commit -m "feat(chat): add Save query action next to View SQL"
```

---

## Task 6: Frontend — dashboard fetches the real saved-queries list + renders workspace stats

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Fetch the real list and add a delete handler**

In `page.tsx`, extend the API import (line 13) and load saved queries inside `loadData()` after the conversations block, then store them on `dashboard.savedQueries`:

```tsx
import { fetchConversations, listSavedQueries, deleteSavedQuery } from "@/lib/api";
```

Inside `loadData()` (after line 52, before `setData(dashboard)`):

```tsx
        try {
          dashboard.savedQueries = await listSavedQueries(token);
        } catch {
          dashboard.savedQueries = [];
        }
```

Update `handleSavedQuerySelect` (lines 76-81) to use `question`:

```tsx
  const handleSavedQuerySelect = useCallback(
    (sq: SavedQuery) => {
      handleSearch(sq.question);
    },
    [handleSearch],
  );
```

Add a delete handler (after `handleSavedQuerySelect`):

```tsx
  const handleSavedQueryDelete = useCallback(
    async (id: string) => {
      const token = (session as any)?.accessToken;
      try {
        await deleteSavedQuery(id, token);
        setData((prev) =>
          prev ? { ...prev, savedQueries: prev.savedQueries.filter((q) => q.id !== id) } : prev,
        );
      } catch {
        /* keep list as-is on failure */
      }
    },
    [session],
  );
```

- [ ] **Step 2: Render `workspaceStats` and pass delete to `SavedQueries`**

After the existing per-user stats grid (lines 122-126), add a workspace section:

```tsx
      {data.workspaceStats && data.workspaceStats.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Workspace activity</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {data.workspaceStats.map((stat) => (
              <StatCard key={stat.label} data={stat} />
            ))}
          </div>
        </div>
      )}
```

Update the `<SavedQueries>` usage (lines 168-171) to pass `onDelete`:

```tsx
          <SavedQueries
            queries={data.savedQueries}
            onSelect={handleSavedQuerySelect}
            onDelete={handleSavedQueryDelete}
          />
```

- [ ] **Step 3: Type-check**

Run: `docker compose -f docker-compose.dev.yml exec -T frontend npx tsc --noEmit`
Expected: PASS (no errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat(dashboard): fetch real saved queries + render workspace stats"
```

---

## Task 7: Full verification (smoke + visual)

**Files:** none (verification only)

- [ ] **Step 1: Backend suite**

Run: `docker compose -f docker-compose.dev.yml exec -T backend pytest backend/tests/test_dashboard.py backend/tests/test_saved_queries.py -v`
Expected: all PASS.

- [ ] **Step 2: Done-check gate**

Run: `bash smoke/done-check.sh`
Expected: exit 0 (BE + FE tests + API-has-UI + boot/login smoke).

- [ ] **Step 3: Visual verify via Playwright**

Drive `aria.localhost`: log in, open the dashboard. Confirm the "Workspace activity" cards show non-zero numbers (≥138 Workspace Queries for the active workspace) and the chart shows the 7-day workspace trend. Open `/chat`, run a query, click **View SQL → Save query**, return to the dashboard **Saved Queries** tab, confirm the saved item appears and that delete (✕) removes it. Screenshot both states.

- [ ] **Step 4: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "test(dashboard): smoke + visual verification for dashboard data and saved queries"
```

---

## Self-Review Notes

- **Spec coverage:** "fix user_id write" → Task 2 (warn + helper; valid-UUID attribution proven by regression test). "workspace summary" → Task 1 + Task 6. "Saved Queries tam bağla" → Save action (Task 5), real list fetch + delete (Task 4, Task 6), type unification (Task 3).
- **Known constraint (call out to the user):** per-user attribution still requires the JWT `sub` to be a real UUID. With the dev `admin-001` identity, the *per-user* cards stay 0 by design; the *workspace* cards carry the real numbers. Fully fixing per-user attribution in dev is a Keycloak/token-claim change, out of scope here.
- **Type consistency:** `SavedQuery` uses `question`/`sql`/`created_at` everywhere after Task 3; `onDelete?: (id: string) => void` matches `handleSavedQueryDelete`.
- **Verify-before-code:** confirm `TokenUsageDaily.customer_id` exists (Task 1, Step 3) before using it; confirm `backend/tests/test_admin_metrics.py` fixture names before reusing them.
