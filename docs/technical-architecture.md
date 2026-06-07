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

## Data Model (12 tables)

customers, teams, users, customer_db_configs, queries, query_history,
artifacts, background_jobs, memory_entries, schema_relationships,
token_quotas, token_usage_daily

> **Note:** vault_knowhow table REMOVED — schema metadata now lives in Obsidian
> vault at `docs/vaults/{workspace_id}/tables/*.md` (MinIO sync optional).

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
| users | memory_entries | RESTRICT | Admin UI manual delete |
| users | token_usage_daily | CASCADE | MinIO JSON backup before delete |
| teams | users | RESTRICT | |

## Auth & RBAC

| Role | can_view_sql | can_manage_team | can_admin |
|------|-------------|-----------------|-----------|
| admin | ✅ | ✅ | ✅ |
| team_lead | ✅ | ✅ | ❌ |
| analyst | ✅ | ❌ | ❌ |
| viewer | ❌ | ❌ | ❌ |

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

## Row Governance

- Dry-run: EXPLAIN PLAN before execution
- Row limit: admin-configurable per-customer (default 10K)
- Admin/team_lead exceed → Prefect background → MinIO presigned URL (3-day)
- Others exceed → blocked with warning

## Token Quotas

3-layer: session (100K) → user (500K) → team (2M)
Admin-configurable. Local LLMs counted. Redis counters + PostgreSQL persistence.

## SQL Visibility

Per-role + per-user override. Default: admin + team_lead + analyst see SQL.
Admin can change `show_sql_to_roles` per customer.

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
| 4. Query Execution | DatabaseExecutor | Customer DB (Oracle/PG/MySQL/MSSQL) | DataFrame |
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
