# ARIA — Gap Analysis (planned-but-unwired / stubbed)

> Generated 2026-06-29 via 4 parallel code audits (plans · backend stubs · frontend↔backend wiring ·
> security/invariants). Headline findings (export dead-end, BackgroundJob/Prefect inert, hardcoded
> credentials) surfaced independently from multiple audits → high confidence. Tracks remediation in
> branch `fix/gap-analysis-remediation`. Tick items as they land.

## 🔴 TIER 1 — CRITICAL (security + data loss + broken headline feature)

| # | Gap | Evidence | Problem | Status |
|---|-----|----------|---------|--------|
| 1 | **Backup-before-delete invariant NOT implemented** | AGENTS.md hard rule; no `backup`/`soft-delete`/`deleted_at` anywhere | `customers` `ON DELETE CASCADE` → deleting a customer hard-deletes `queries`+`token_usage_daily`+`background_jobs` with **no backup**. Most serious invariant breach. | ✅ |
| 2 | **Master KEK hardcoded fallback** | `backend/app/services/crypto.py:68` `ARIA_SECRET_KEY` default `"fallback_secret_key_for_dev_only_change_in_prod"` + static salt `b"aria_salt"` | If env unset, the key wrapping **every customer DB password** is forgeable. | ✅ |
| 3 | **Keycloak admin `admin/admin` hardcoded** | `backend/app/services/keycloak_admin.py:16-17` | Hardcoded secret; breaks against non-bootstrap prod KC. | ✅ |
| 4 | **Default user password `123456` (non-temp)** | `keycloak_admin.py:53`; `admin/users.py` passes no password | Every admin-created user silently gets `123456`, never surfaced/rotated. | ✅ |
| 5 | **Large-result export dead-end** | `pipeline.py:1396` fire-and-forget; `worker/tasks.py:66` returns URL but it's discarded; no FE `export`/`download` SSE case | >5000 rows → user told "link will be provided" but **nothing ever delivers it**; `BackgroundJob` never created. | ✅ |

## 🟠 TIER 2 — HIGH (promised-but-broken / unwired functionality)

| # | Gap | Evidence | Status |
|---|-----|----------|--------|
| 6 | **Token quota bypassable** | `pipeline.py:2073` fails-OPEN on exception; skipped for non-UUID user_id; "session" = conversation id → resets on new chat | ✅ |
| 7 | **RBAC holes — 6 mutating endpoints unguarded** | 4 vault-write (`workspaces.py:448,632,1132,1190`) + 2 schema-cache (`schema.py:83,113`) → any authed user poisons workspace NL2SQL grounding | ✅ |
| 8 | **No security headers** | `main.py:116` only CORS; no CSP/HSTS/X-Frame-Options/nosniff | ✅ |
| 9 | **Rate limiting near-absent** | `query.py:202` only `POST /api/query`; public `POST /api/onboarding/register` + all admin unlimited | ✅ |
| 10 | **`sync_user_from_token` dead (0 callers)** | `auth/sync.py:13` — JWT-only users get no local `users` row → quota/audit/SQL-visibility silently degrade | ✅ |
| 11 | **Hardcoded `stc-kuwait` workspace fallback** | FE `page.tsx:37`, `chat/page.tsx:125`, `api.ts:136` + BE `dependencies.py:170` → cross-tenant data risk for non-STC tenants | ✅ |
| 12 | **"Queries Today" always 0** | `metrics.py:54` reads non-existent `DataAuditLog.timestamp` → broad except → 0 | ✅ |
| 13 | **MONTHLY token quotas never enforced** | `token.py:105` `if period != daily: continue` | ✅ |
| 14 | **"Saved Queries" entirely unwired** | `dashboard.py:128` `savedQueries: []` hardcoded; no save endpoint | ✅ |
| 15 | **Team-invite password hardcoded** `"TempPassword123!"` | `settings/team/page.tsx`; planned `/api/workspaces/{id}/users` endpoint missing | ✅ |
| 16 | **EXPLAIN guard no-op for MySQL/MSSQL** | no `explain()` override → `estimated_rows:0` → massive-query guard silently off | ✅ |
| 17 | **Retry logic false-positive** | `@retry` on `verify_sql_security` (no DB call); real `execute_query`/LLM call have no retry | ☐ |

## 🟡 TIER 3 — MEDIUM

| # | Gap | Evidence | Status |
|---|-----|----------|--------|
| 18 | **Prefect entirely inert** | `BackgroundJob`+`prefect_flow_run_id` + dev Prefect containers, but 0 flows/deployments, absent from prod, Plan 2 reconcile never written | 🔄 chunks 1-3 done (app-code + reconcile flow, tested); chunk 4 (prod Prefect infra) deferred — see below |
| 19 | **LLM chart-selection subsystem dead** | `pipeline.py:1649` `use_llm=False` constant → all of `agents/chart_llm.py` unreachable | ✅ |
| 20 | **`Artifact` DB model/table fully dead** | never written → dashboard "Saved Artifacts: 0" placeholder (`dashboard.py:111`) | ✅ |
| 21 | **Memory-stats wrong namespaces** | `service.py:647,657` `team:default` + `:user` → admin shows ~0 team/user memories | ✅ |
| 22 | **Memory decay dormant** | `cleanup_expired_memories` only manual admin `POST /cleanup`; no scheduler | ✅ |
| 23 | **Sprint 9 QueryTrace + admin conversation-debug UI never built** | no `trace` field on `ConversationMessage`; no `/admin/conversations` | ✅ BE+FE shipped, tested & visually verified |
| 24 | **`/admin` Overview + `/settings` index = `return null`** (blank page) | `app/admin/page.tsx`, `app/settings/page.tsx` | ✅ |
| 25 | **CSV download link lost on reload** | `csv_url` not persisted in `ConversationMessage` | ✅ |
| 26 | **Two-way vault sync (Obsidian↔MinIO) is fiction** | `vault_sync.py` one-way only | ❎ closed |
| 27 | **LLM config "Phase 1" passthrough virtual key** | `llm_resolver.py:113` — upstream key used as proxy key; no per-customer isolation | ☐ |
| 28 | **JWT audience check disabled** | `jwt.py:119` `verify_aud:False` → accepts another client's token in the realm | ✅ |
| 29 | **`keycloak_verify_ssl=False` default** + **Oracle `stc/stc123` dummy fallback** in live path | `config.py:61`, `pipeline.py:1031` (non-prod) | ✅ |
| 30 | **`keycloak_admin.delete_user`/`create_team_group` unwired** | team KC group not created; user delete not propagated | ⏸ migration |
| 31 | **`/api/admin/metrics` no UI** + **onboarding self-register no abuse control** + **user↔team 1–1 not schema-enforced** (nullable) | | ☐ |

## ⚪ TIER 4 — LOW / cosmetic

- `getMockDashboardData()` dead code (said removed, still present)
- hardcoded fallback suggestions (`suggestions.py:61`)
- `ColumnInfo.comment` never populated (vault descriptions always heuristic)
- telecom-biased regex descriptions (`vault_generator.py:237`)
- `_detect_user_correction` dead (`pipeline.py:53`)
- `_resolve_model` placeholder returns `gpt-4o` (`agents/chart_llm.py:208`)
- `chart_html` vestigial field
- token dashboard has no charts; memory detail modal missing; per-stage timeout + circuit breaker missing
- `background_worker` health probe is a no-op
- `console.log` token-prefix leak (`frontend/src/lib/api.ts:211`)
- audit `success` filter reads a never-written field (`audit.py:257`)

## ✅ Verified solid (NOT gaps)

RLS (fail-closed) + CLS + per-user SQL-visibility (server-side strip) · SELECT-only guard (lexical + sqlglot AST) ·
DB password encryption · audit logging + UI · resumable streaming Plan 1 · insight SSE + clickable suggestion chips ·
team-convention approval gating · memory proactivity · onboarding flow · CMEK rotation/status UI · BYOK ·
per-customer i18n · (recent) MinIO endpoint + Kaleido PNG + mem0 2.x + hybrid retrieval.

## 🔁 Recurring anti-pattern

Many gaps **fail silently** via broad `try/except` returning zeros/canned data (wrong column, unenforced quota,
lost export result) — invisible without this audit. Remediation should prefer fail-loud over silent fallback.


---

## Remaining work (snapshot 2026-06-29)

**Done & merged to main:** TIER 1 (1–5), TIER 2 (6–17), TIER 3 19,20,21,22,24,25,28,29, TIER 4 (console.log token-leak, dead `_detect_user_correction`). Item 26 CLOSED (not a gap — vault is intentionally one-way DB→md→Qdrant; Obsidian/MinIO sync never existed). Items 17 & audit-`success`-filter were audit false-positives (no change). Item 15 verified DONE (FE posts `/api/admin/users` passwordless; backend mints a one-time temp password — folded into TIER 1 item 4).

### 25 — CSV download link lost on reload — DONE
`csv_url` added to `ConversationMessage` and persisted at both pipeline build sites (Stage-6 `assistant_msg` + resume chart re-append); FE history reload now restores `csv_url` onto the rebuilt `chartSpec`. Guard: `backend/tests/test_conversation_csv_persist.py`.

### 18 — Prefect deploy-durability (Plan 2) — chunks 1-3 DONE, chunk 4 DEFERRED
Spec: `docs/superpowers/specs/2026-06-28-durable-resumable-chat-streaming-design.md`.

**Done & tested (app-code durability layer):**
1. ✅ Heartbeat wired into the detached producer (`backend/app/api/query.py`): a
   `run_store.maintain_heartbeat` task renews the run lock for the lifetime of
   generation, so a long-but-alive run never lapses / is never falsely reclaimed.
   The POST handler also persists the run's full gating context (question,
   db_config_id, workspace_id, user_id, team_id, sql_visible) into run-meta on
   `acquire_run`. Tests: `backend/tests/test_query_resume.py`,
   `backend/tests/test_run_store_plan2.py`.
2. ✅ `backend/app/flows/reconcile.py` — `reconcile_stalled_runs` flow + pure
   `reconcile_stalled_runs_core(redis, engine)`: `find_running_cids` →
   `reclaim_stale_run` (atomic SET NX fencing) → re-run idempotently with the
   PERSISTED context (no JWT). A live run (lock held) is never stolen; a run
   with no context is failed terminally (not left running forever). Prefect
   `@flow` decoration is lazy (`get_reconcile_flow()`) so the core unit-tests
   need no Prefect server. Tests: `backend/tests/test_reconcile.py`.
3. ✅ `process_query(resume=True)` skips re-appending the user message on a
   reconcile re-run. Test: `backend/tests/test_pipeline_resume.py`.

**Chunk 4 — DEFERRED (LOCKED-DECISIONS-level infra; needs explicit sign-off):**
Adding Prefect to prod is flagged in the spec (§Risks, "confirm before the
compose change ships") because it introduces new prod services. Remaining steps
for a separate infra PR:
- `docker-compose.prod.yml`: add `prefect-server` + `prefect-db` + a
  `prefect-worker` service & work-pool; wire `PREFECT_API_URL` into backend +
  worker (mirror the dev `prefect-server`/`prefect-db` already in
  `docker-compose.dev.yml`).
- Register the reconcile deployment from `get_reconcile_flow()` on a ~60s
  schedule against the prod work-pool (e.g. a `prefect deploy` step / entrypoint).
- Record `prefect_flow_run_id` on the reconciled run (column already reserved on
  `artifact.py`).
Until chunk 4 ships, the reconcile flow exists and is tested but is not scheduled
in prod, so a producer killed by a deploy still leaves its run to lapse on the
lock TTL rather than being re-run — the live SSE fast-path + resume (Plan 1) are
unaffected.

### 23 — QueryTrace + admin conversation-debug UI — DONE (visual screenshot pending)
Shipped as a vertical slice:
- `backend/app/query/trace.py::build_query_trace` + `ConversationMessage.trace`
  (optional, backward-compatible); the pipeline captures the resolved model and
  attaches the trace at Stage 6. Tests: `backend/tests/test_query_trace.py`.
- `/api/admin/conversations` + `/{cid}` (require_role(ADMIN), workspace-scoped via
  `list_workspace_conversations` scanning `aria:conv:{ws}:*`). Tests:
  `backend/tests/test_admin_conversations.py` (incl. route-table RBAC introspection).
- FE `/admin/conversations` screen + nav link, mirroring the admin audit-log page.
Verification: backend suite green (250); FE `tsc --noEmit` + `eslint` clean; the new
route compiles & serves 200 in the live Next dev server. Visual-verified by driving
the live stack with the project's own Playwright (admin login → `/admin/conversations`):
the list renders real workspace conversations and the detail dialog renders each
turn's message + SQL. (The browser MCPs were unavailable this session, so a standalone
Playwright script was used instead.) Note: the live QueryTrace badge only appears for
turns produced AFTER the backend image is rebuilt — the running `aria-backend`
predates the Stage-6 trace wiring, so existing turns have `trace=null` (rendered
correctly as no badge).

### 27 — BYOK per-customer virtual key (Phase 2) — MEDIUM (crypto — careful)
`llm_resolver` uses the customer's upstream key directly as the proxy key ("Phase 1 passthrough"). Phase 2: mint/decrypt a per-customer LiteLLM virtual key. Touches `crypto`/key management — review carefully.

### 30 — Keycloak team-group / delete-user — MEDIUM (needs migration)
`create_team` writes only a DB row (no KC group); `delete_team` deletes by the wrong id (`team.id`, not the KC group id). Clean fix needs a `teams.kc_group_id` column (migration) + wire `create_team_group(name)` on create + use it on delete + a backfill for existing teams. Matters because JWT `groups` claims drive team-scoped SSO/RLS.

### 31 — user↔team 1–1 not schema-enforced — MEDIUM (migration, risky)
`User.team_id` is nullable & non-unique; "exactly one team" isn't enforced. Adding NOT NULL/constraints needs a migration + a data-cleanup of existing rows.

### TIER 4 remaining (low/cosmetic)
`chart_html` vestigial field (verify FE before removing); `ColumnInfo.comment` never populated (needs discovery-SQL change); telecom-biased regex descriptions + hardcoded fallback suggestions (intentional graceful fallbacks — keep); token dashboard has no charts / memory detail modal (FE features).
