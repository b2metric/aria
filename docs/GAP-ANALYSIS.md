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
| 15 | **Team-invite password hardcoded** `"TempPassword123!"` | `settings/team/page.tsx`; planned `/api/workspaces/{id}/users` endpoint missing | ☐ |
| 16 | **EXPLAIN guard no-op for MySQL/MSSQL** | no `explain()` override → `estimated_rows:0` → massive-query guard silently off | ✅ |
| 17 | **Retry logic false-positive** | `@retry` on `verify_sql_security` (no DB call); real `execute_query`/LLM call have no retry | ☐ |

## 🟡 TIER 3 — MEDIUM

| # | Gap | Evidence | Status |
|---|-----|----------|--------|
| 18 | **Prefect entirely inert** | `BackgroundJob`+`prefect_flow_run_id` + dev Prefect containers, but 0 flows/deployments, absent from prod, Plan 2 reconcile never written | ☐ |
| 19 | **LLM chart-selection subsystem dead** | `pipeline.py:1649` `use_llm=False` constant → all of `agents/chart_llm.py` unreachable | ✅ |
| 20 | **`Artifact` DB model/table fully dead** | never written → dashboard "Saved Artifacts: 0" placeholder (`dashboard.py:111`) | ✅ |
| 21 | **Memory-stats wrong namespaces** | `service.py:647,657` `team:default` + `:user` → admin shows ~0 team/user memories | ✅ |
| 22 | **Memory decay dormant** | `cleanup_expired_memories` only manual admin `POST /cleanup`; no scheduler | ✅ |
| 23 | **Sprint 9 QueryTrace + admin conversation-debug UI never built** | no `trace` field on `ConversationMessage`; no `/admin/conversations` | ☐ |
| 24 | **`/admin` Overview + `/settings` index = `return null`** (blank page) | `app/admin/page.tsx`, `app/settings/page.tsx` | ✅ |
| 25 | **CSV download link lost on reload** | `csv_url` not persisted in `ConversationMessage` | ☐ |
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
