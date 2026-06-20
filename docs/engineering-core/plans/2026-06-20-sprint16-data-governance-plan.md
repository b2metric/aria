# Sprint 16: Enterprise Data Governance — Row & Column Security

> **For agentic workers:** REQUIRED SUB-SKILL: use engineering-core:subagent-driven-development or engineering-core:executing-plans to implement this plan task-by-task. Each task is a vertical slice: tests-first → backend → Next.js admin surface → visual-verify → green smoke.

**Goal:** Close the **P0 enterprise sales blocker** identified in the 2026-06-20 competitive analysis — **Row-Level Security (RLS)** — plus the adjacent access-control gaps that cluster with it. Today ARIA enforces only *table-level* access (`TeamVaultPolicy.allowed_tables`, pruned in `pipeline.py`). This sprint adds **row** and **column** scoping on top of that, a per-user raw-SQL visibility control, and full governance auditing — turning ARIA's access story from "which tables" into "which rows, which columns, who sees the SQL."

**Why now:** RLS is the single biggest deal-loser vs. Wren AI / ThoughtSpot / Cortex (all have it); the human-in-the-loop memory approval P0 was already shipped in Sprint 15 Task 3. CLS is half-built (`deny_columns` is modeled but never enforced).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, LiteLLM, Next.js 16, PostgreSQL (control plane), Oracle (tenant data).

**Grounding (existing scaffolding to extend, NOT rebuild):**
- `backend/app/models/governance.py` — `TeamVaultPolicy` (`allowed_tables`, `deny_columns` JSONB, `is_active`) + `DataAuditLog`.
- `backend/app/query/pipeline.py:270` — `TeamVaultPolicy` lookup + `allowed_tables` table-pruning (the enforcement seam to extend).
- `backend/app/services/audit.py` — `AuditService.log_event` (used by Sprint 15 Task 6).
- AGENTS.md:50 — SQL-visibility invariant (raw SQL/results visible only to permitted roles).

> **Out of scope (long-term / post-MVP — tracked in `LOCKED-DECISIONS.md` & `AGENTS.md`, NOT scheduled here):** ClickHouse (Phase 3), Teams/PowerBI/Slack connectors, dbt sync, embedded/white-label API, Go hot-path microservices, Kubernetes/Terraform IaC, vLLM local-GPU routing, two-way vault sync, cloud data-warehouse dialects (BigQuery/Snowflake/Redshift — only PostgreSQL/MySQL/Oracle/MSSQL are implemented today; add cloud DWs demand-driven in Phase 3).

---

### Task 1: Row-Level Security (RLS) — *P0, the anchor*
*Goal: a team/customer only ever sees the rows its policy permits, enforced on the generated SQL — not just trusted to the LLM.*

**Files:**
- Modify: `backend/app/models/governance.py` (add `row_filters`)
- Add: Alembic migration for the new column
- Modify: `backend/app/query/pipeline.py` (apply filters to the executed SQL)
- Modify/Add: `backend/app/api/endpoints/admin/` (vault-policy CRUD incl. row_filters)
- Modify/Add: frontend admin surface for managing row filters
- Add: `backend/tests/test_rls.py`

- [ ] **Step 1: Model + migration** — add `row_filters: JSONB` to `TeamVaultPolicy`, a per-table predicate map, e.g. `{"FCT_SALES": "REGION = 'KW'", "DIM_CUSTOMER": "TENANT_ID = 42"}`. NULL/empty = no row restriction. Alembic migration (control-plane Postgres; run from host venv per the sprint-plan memory).
- [ ] **Step 2: Enforcement on generated SQL** — after table-pruning, rewrite the generated SQL so each filtered table is scoped. Preferred mechanism: **table→filtered-subquery substitution via `sqlglot`** (e.g. `FROM FCT_SALES` → `FROM (SELECT * FROM FCT_SALES WHERE REGION='KW') FCT_SALES`) so the filter is enforced structurally, not by trusting the LLM. Fall back to mandatory-predicate prompt grounding only if a statement can't be safely parsed; if neither can guarantee the filter, **fail closed** (reject the query). Compose with the existing EXPLAIN safeguard.
- [ ] **Step 3: Admin CRUD + UI** — manage `row_filters` per policy (admin only). Surface in the team/vault-policy admin page.
- [ ] **Step 4: Tests** — `test_rls.py`: filter injected for a filtered table; untouched when no policy/filter; multi-table query filters each; fail-closed on unparseable SQL. Live-verify against the Oracle tenant (a filtered query returns only in-scope rows).

---

### Task 2: Column-Level Security (CLS)
*Goal: `deny_columns` is already modeled on `TeamVaultPolicy` but never enforced — make it real.*

**Files:**
- Modify: `backend/app/query/pipeline.py` (schema-context build + result post-filter)
- Modify: `backend/app/api/endpoints/admin/` + frontend (manage `deny_columns`)
- Add: `backend/tests/test_cls.py`

- [ ] **Step 1: Hide denied columns from the LLM** — when building the schema context (`llm_sql._build_schema_context` inputs), drop each policy `deny_columns[table]` entry so the model can't SELECT or reference them.
- [ ] **Step 2: Defense-in-depth result filter** — after execution, strip any denied columns from the result rows (covers `SELECT *` / expression aliases that dodge step 1).
- [ ] **Step 3: Admin UI** — edit per-table column deny-lists on the policy page.
- [ ] **Step 4: Tests** — denied column absent from schema context; absent from results even on `SELECT *`; no-policy path unchanged.

---

### Task 3: Per-user SQL-visibility override + governance audit
*Goal: honor the AGENTS.md SQL-visibility invariant with per-user control, and record every RLS/CLS action for compliance.*

**Files:**
- Modify: `backend/app/models/` (user-level `sql_visibility` override) + migration
- Modify: backend query/response path (gate raw SQL + raw results on the override)
- Modify: `backend/app/api/endpoints/admin/users*` + frontend user admin
- Modify: `backend/app/query/pipeline.py` (audit RLS/CLS applications via `AuditService`)

- [ ] **Step 1: Per-user override** — add an optional per-user `sql_visibility` flag that overrides the role default (who may see the raw SQL string + raw SQL result), per the AGENTS.md invariant. Default = inherit role.
- [ ] **Step 2: Enforce in the response** — when a user lacks visibility, omit the SQL string + raw rows from the chat/query response (chart/summary still returned).
- [ ] **Step 3: Governance audit** — write a `DataAuditLog` entry whenever RLS row filters / CLS column denials are applied (action e.g. `rls_filter` / `cls_denied`, details = table + predicate/columns), so the audit log shows what was restricted.
- [ ] **Step 4: Admin UI + tests** — toggle visibility per user; unit-test the gate + the audit writes.

---

### Task 4: Hygiene — dead tables + Dependabot
*Goal: round out the sprint by clearing known debt.*

**Files:**
- Add: Alembic migration dropping the dead tables
- Dependabot PRs (review + merge)

- [ ] **Step 1: Drop dead tables** — `memory_entries` + `vault_knowhow` are modeled + migrated but never read (confirm with a repo grep first). Add a migration that drops them; remove the orphan models if present.
- [ ] **Step 2: Dependabot** — review and merge the 4 open Dependabot PRs (CI must stay green).

---

> **Definition of done (every task):** tests-first, backend + Next.js surface where user-facing, `ruff`/`eslint`/`tsc` clean, live run-evidence (RLS/CLS verified against the Oracle tenant; visibility verified in the UI), green CI, branch→PR→merge. Per CLAUDE.md: no "done" without cited run-evidence.
