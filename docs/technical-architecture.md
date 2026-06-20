# ARIA — Conversational BI: Technical Architecture

> **Version:** 2.0 | **Date:** 2026-06-07 | **All decisions resolved**

## Tech Stack

| Layer | Tech | Purpose |
|-------|------|---------|
| Backend | Python 3.12 + FastAPI | NL2SQL pipeline, API, agent logic |
| WSGI | Gunicorn + Uvicorn workers (4) | Multi-worker, graceful restart |
| Reverse Proxy | Traefik 3 | SSL termination, load balancing, rate limiting, routing |
| Frontend | Next.js 16 + shadcn/ui v4 | Chat UI, admin, dashboard |
| Metadata DB | PostgreSQL 16 | customers, queries, artifacts, memory_entries |
| Cache | Redis 7 | Schema cache, rate limit, token counters |
| Vector DB | Qdrant | Mem0 long-term memory embeddings |
| Workflow | Prefect 3 | Background high-row-count reports |
| Auth | Keycloak 26 | OIDC + RBAC + API keys |
| Artifact Store | MinIO | Plotly HTML/CSV, report exports |
| LLM Proxy | LiteLLM | Multi-model routing, cost tracking |
| CI/CD | GitHub Actions | lint → test → security → deploy |

## Data Model (core tables)

customers, teams, users, customer_db_configs, queries, query_history,
artifacts, background_jobs, schema_relationships, token_quotas,
token_usage_daily, team_vault_policies, data_audit_logs

> **Note (Sprint 16):** `memory_entries` and `vault_knowhow` tables REMOVED —
> both were modeled but never read. Agent memory lives in Mem0 + Qdrant; schema
> metadata lives in the Obsidian vault at `docs/vaults/{workspace_id}/tables/*.md`
> (MinIO sync optional).

## FK Cascade Decisions

| Parent | Child | Cascade | Note |
|--------|-------|---------|------|
| customers | teams | CASCADE | |
| customers | customer_db_configs | CASCADE | |
| customers | token_usage_daily | CASCADE | MinIO JSON backup before delete |
| customers | token_quotas | CASCADE | |
| queries | artifacts | CASCADE | |
| queries | query_history | CASCADE | |
| queries | background_jobs | CASCADE | MinIO JSON backup before delete |
| users | token_usage_daily | CASCADE | MinIO JSON backup before delete |
| teams | users | RESTRICT | |

## Auth & RBAC

| Role | can_view_sql | can_manage_team | can_admin |
|------|-------------|-----------------|-----------|
| admin | ✅ | ✅ | ✅ |
| team_lead | ❌ | ✅ | ❌ |
| analyst | ✅ | ❌ | ❌ |
| viewer | ❌ | ❌ | ❌ |

> `can_view_sql` above is the **role default** (`_can_view_sql` = admin + analyst). A
> per-user `User.sql_visibility` override can flip it either way — see [SQL Visibility](#sql-visibility).

Token: silent refresh, access 15min / refresh 8h, Keycloak OIDC + PKCE.

## Long-Term Memory

- **Mem0 2.x**: extraction + embedding logic + graph-based deduplication
- **Qdrant**: vector storage + semantic search (NO pgvector)
- **PostgreSQL**: structured metadata + CRUD + approval workflow
- Dual write: user memory + team memory (same transaction)
- Human-in-the-loop: team_lead approval, admin CRUD dashboard

### Embedding Configuration (2026-06-07)

| Setting | Value | Notes |
|---------|-------|-------|
| Provider | Gemini via LiteLLM | OpenAI quota exceeded, switched to gemini-embedding-001 |
| Model | `gemini-embedding` | Alias in LiteLLM config |
| Dimensions | **3072** | Must match in both `vector_store.embedding_model_dims` and `embedder.embedding_dims` |
| Collection | `aria_memory` | Auto-created by Mem0 with correct dims |

**Critical:** If embedding model changes, delete Qdrant collection and let Mem0 recreate it with correct dimensions.

## Row & Column Governance

Per-team policies live on `TeamVaultPolicy` (`allowed_tables`, `row_filters`, `deny_columns`), resolved per `(customer, team)` with the team-specific policy preferred over the customer-wide default.

- **Table-level (layer 0):** `allowed_tables` whitelist — non-allowed tables pruned from the schema context and blocked at execution.
- **Row-Level Security (Sprint 16):** `row_filters` — per-table SQL predicates (e.g. `{"FCT_SALES": "REGION = 'KW'"}`) injected **structurally** into the generated SQL via `sqlglot` (table → filtered subquery), enforced on the executed query, never trusted to the LLM. **Fails closed**: if a filtered table's statement can't be safely rewritten, the query is rejected.
- **Column-Level Security (Sprint 16):** `deny_columns` — denied columns dropped from the LLM schema context (prevention) **and** stripped from result rows (defense-in-depth, covers `SELECT *`).
- **Governance audit:** each RLS/CLS enforcement writes a `DataAuditLog` row (`rls_filter` / `cls_denied`) via `AuditService`, only when something was actually restricted.

**Row limits (orthogonal):**
- Dry-run: EXPLAIN PLAN before execution
- Row limit: admin-configurable per-customer (default 10K)
- Admin/team_lead exceed → Prefect background → MinIO presigned URL (3-day)
- Others exceed → blocked with warning

## Token Quotas

3-layer: session (100K) → user (500K) → team (2M)
Admin-configurable. Local LLMs counted. Redis counters + PostgreSQL persistence.

## SQL Visibility

- **Role default:** admin + analyst may see the raw SQL string + raw results (`_can_view_sql`); team_lead + viewer cannot.
- **Per-user override (Sprint 16):** `User.sql_visibility` (`bool | NULL`; NULL = inherit role) overrides the role default per user, editable in the admin Users UI.
- **Enforcement:** when a user lacks visibility, the chat/query response omits the SQL string + the raw `table` result; the chart visualization + insight are still returned (deliberate product choice). **Fails closed** — a DB error while resolving the override hides SQL rather than leaking it.

## Vault Architecture

- **Primary**: MinIO — `vaults/{customer_id}/{db}/{table}.md`
- **Local sync**: Obsidian vault pull for manual editing
- **Two-way**: ARIA UI → MinIO → local Obsidian, Obsidian edit → MinIO → ARIA

## Response Pipeline

> **Detaylı akış:** [pipeline-flow.md](./pipeline-flow.md)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Memory  │───▶│  Vault   │───▶│   SQL    │───▶│  Chart   │───▶│ Insight  │
│  Lookup  │    │ Matching │    │   Gen    │    │   Gen    │    │   Gen    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
  Qdrant         Obsidian       Rule-based      Plotly JSON      LLM-based
  semantic       vault .md      + LLM fallback  + MinIO HTML     analysis
  search         keyword match
```

| Stage | Component | Data Source | Output |
|-------|-----------|-------------|--------|
| 1. Memory Lookup | Mem0 + Qdrant | User/team memories | MemoryContext |
| 2. Vault Matching | SemanticMatcher | `docs/vaults/{workspace}/tables/*.md` | MatchedTables |
| 3. SQL Generation | RuleBasedGen / LLMSQLGen | Vault schema + memory | SQL string |
| 4. Query Execution | DatabaseExecutor | Customer DB (Oracle/PG/MySQL/MSSQL) | DataFrame (w/ Semantic Self-Correction on errors) |
| 5. Chart Generation | ChartGenerator | Query result | Plotly spec |
| 6. Insight Generation | InsightGenerator | Result + memory | Summary + suggestions |
| 7. Memory Store | MemoryService | Successful query | Cached for future |

## Resolved Decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Memory solution | Mem0 + Qdrant |
| 2 | Sandbox execution | Flag-only (prod perf) |
| 3 | Ollama | Optional, NOT default |
| 4 | ClickHouse | Phase 3 |
| 5 | Go microservice | REMOVED |
| 6 | pgvector | REMOVED (Qdrant handles embeddings) |
| 7 | Token refresh | Silent refresh (A) |
| 8 | Reverse proxy | Traefik 3 (nginx KULLANILMAZ) |
| 9 | Embedding model | Gemini embedding-001 (3072 dims) via LiteLLM |

## Production Deploy Architecture

```
Internet
  │
  ▼
Traefik 3 (SSL via Let's Encrypt)
  ├── /api/*          → Gunicorn (4x Uvicorn workers) → FastAPI :8000
  ├── /               → Next.js :3000 (or Vercel)
  ├── /minio          → MinIO :9000
  ├── /auth           → Keycloak :8080
  └── health checks   → all backends
       │
       ├── Rate limiting (per IP + per customer JWT claim)
       └── Circuit breaker (3 failures → 30s cooldown)
```

**Gunicorn config:**
```
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 app.main:app
```

**Why Traefik over Nginx:**
- Docker-native: auto-discovers containers via labels
- Let's Encrypt: automatic SSL cert renewal
- Middleware: rate limit, circuit breaker in YAML
- Dashboard: built-in web UI on :8080
- No config reload needed on container changes

---

## Engineering-core gates & hybrid LLM routing (added 2026-06-11)

The repo now follows the **engineering-core** discipline (hermes-toolkit `skills/engineering-core`). Architecture is anchored in `LOCKED-DECISIONS.md` (compaction-immune ADR ledger) + `AGENTS.md` (read-first).

**Hard gates (enforced in code/CI, not prose):**
- **Boot+login smoke** — `smoke/check.sh` + CI `smoke-boot` job. Health → Keycloak JWKS (`/auth` path) → OIDC login round-trip → authenticated `GET /me`. Run: `bash smoke/check.sh` (auto-reads `backend/.env`; targets `http://api.aria.localhost`, client `aria-web`). No "done" on a full-stack change without a green smoke.
- **Backend startup validation** — `backend/app/main.py` lifespan + `core/config.py` `validate_runtime()`: fails loudly on dummy/missing `LITELLM_API_KEY` (no silent `sk-1234`) and unreachable Keycloak JWKS. Bypass for offline/tests: `ARIA_SKIP_STARTUP_CHECKS=1`.
- **Frontend** — `SafeIframe.tsx` refuses `srcDoc > 1 MB` (the 5 MB Plotly React-crash); charts render from JSON (`chart_data`) via recharts.
- **Repo-path guard** — `.githooks/pre-commit` (`core.hooksPath=.githooks`): blocks scratch files, >2 MB blobs, nested repos, ground-truth-doc deletion.

**Hybrid LLM routing** (`infra/llm/config.yaml`, LiteLLM behind Traefik at `llm.aria.localhost` / `langfuse.aria.localhost`):
per-role aliases (`role-architect|lead-dev|backend-codegen|frontend-vision|debugger|reviewer|qa-gate|bulk-worker`), **reviewer ≠ author** via `review-of-<family>` chains, hybrid cloud + local **vLLM** (`local-thinking|vision|embed` via `LOCAL_LLM_BASE`, RTX 6000 — see `infra/llm/RUNBOOK-local-serving.md`), per-role `cost_per_token`, fallbacks crossing local↔cloud. Stack policy: **Python/FastAPI first; Go only for a measured hot path** (engineering-core:stack-decision).

## 10. Multi-Tenant Security & BYOK

ARIA implements a stringent security model designed for enterprises (like banking and health sectors):

- **Read-Only SQL Guards:** `verify_read_only_sql` intercepts generated queries before execution to block DML/DDL (UPDATE, DROP, etc.) natively in python.
- **BYOK (Bring Your Own Key):** Enterprise customers can provide their own OpenAI/Azure API keys (`CustomerLLMConfig`). ARIA routes queries using `llm_resolver.py` directly to the provided models, circumventing the shared platform key.
- **CMEK (Customer Managed Encryption Keys):** To support enterprise compliance, ARIA implements Envelope Encryption. Each tenant is assigned a unique Data Encryption Key (DEK). This DEK is then wrapped/encrypted by a Key Encryption Key (KEK) which can be the default application key (App KEK) or a customer-provided KMS key (AWS KMS, GCP KMS, Azure Key Vault) via `CustomerKeyConfig`.
- **Database Password Decryption:** Credentials stored in `CustomerDBConfig` (as well as LLM API Keys) are encrypted at rest using the tenant's DEK (`services/crypto.py`) and decrypted dynamically at runtime during the pipeline execution.
