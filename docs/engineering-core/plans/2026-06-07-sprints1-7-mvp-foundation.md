# Sprints 1–7: MVP Foundation *(retroactively documented)*

> **Status: shipped.** This file is a retroactive ledger of the foundational features built during the MVP era (commit `021b43a` "ARIA MVP Sprint 1-6", 2026-06-07) and Sprint 7 (2026-06-08…06-12), which predate the `docs/engineering-core/plans/` folder — the first per-sprint plan file is Sprint 8 (2026-06-13). None of the items below were tracked in a sprint plan; they are recorded here so the plan folder reflects the *whole* system, not just Sprint 8+.

**How this was found:** codebase + git-history audit cross-referenced against all sprint plans (2026-06-20). Every item below is `git`-dated to the 06-07…06-12 window and absent from Sprints 8–15.

---

### Task 1: Multi-database connectivity & schema introspection
- [x] **Generic multi-DB executor** — one executor over PostgreSQL / MySQL / Oracle / MSSQL (the 4 dialects registered in `_EXECUTORS`) with per-dialect SQL + per-connection row limits. `backend/app/db/executor.py` (06-07). **(RESOLVED — retroactive)** *(Cloud data-warehouses — BigQuery / Snowflake / Redshift — are NOT implemented; parked as future work — see Sprint 16 plan "Out of scope".)*
- [x] **Schema introspection** — per-dialect discovery of tables, columns, PK/FK, row counts. `backend/app/schema_discovery/discovery.py` (06-07). **(RESOLVED — retroactive)**

### Task 2: Knowledge vault (data dictionary)
- [x] **Obsidian vault generator** — Markdown + YAML-frontmatter per table, with keyword inference; **enrichment** merges external metadata (business glossary / Excel); in-memory **schema cache**. `backend/app/schema_discovery/{vault_generator,enrichment,cache}.py` (06-07). **(RESOLVED — retroactive)**
- [x] **Data Dictionary editor UI** — `/admin/schema`: browse tables, edit descriptions + keywords + column descriptions, manual relationship CRUD, re-sync trigger. `frontend/src/app/admin/schema/page.tsx` (06-12, Sprint 7). **(RESOLVED — retroactive)** *(Sprint 13 Task 3 later added vault **auto-sync** on top of this base.)*

### Task 3: Query pipeline (core)
- [x] **NL→SQL pipeline + SSE streaming** — natural-language → SQL via LiteLLM, streamed status events (thinking / generating_sql / sql_ready / executing / rendering_chart / complete). `backend/app/query/pipeline.py`, `backend/app/api/query.py` (06-07). **(RESOLVED — retroactive)**
- [x] **Conversation history** — Redis-backed multi-turn conversation + message storage with CRUD. `backend/app/query/conversation.py` (06-07). **(RESOLVED — retroactive)**

### Task 4: Charts & artifacts
- [x] **Chart pipeline (base)** — zero-LLM heuristic chart proposer + Recharts-JSON / CSV renderer + builder orchestration. `agents/chart_{heuristic,builder,renderer}.py` (06-07). *(LLM refiner + Kaleido PNG came later — Sprint 13/15.)* **(RESOLVED — retroactive)**
- [x] **Artifact store + vault** — MinIO upload, presigned / public URLs, JSON archive backup + cleanup/retention policy. `agents/artifact_store.py`, `agents/artifact_vault.py` (06-07). **(RESOLVED — retroactive)**

### Task 5: Auth & RBAC
- [x] **Keycloak JWT auth + RBAC** — OIDC token validation, role hierarchy (viewer < analyst < team_lead < admin), permission gates, robust federated logout. `backend/app/auth/{jwt,dependencies,rbac,models}.py` (06-07; logout hardening 06-12). **(RESOLVED — retroactive)**

### Task 6: Memory (Mem0 + Qdrant)
- [x] **Memory service (base)** — user / team / query-cache memory over Mem0 + Qdrant (migrated off pgvector). `backend/app/memory/service.py` (06-07; pgvector→Qdrant 06-12). *(Sprint 8 later "completed" memory: TTL, admin UI, preference extraction.)* **(RESOLVED — retroactive)**

### Task 7: LLM infrastructure & observability
- [x] **Hybrid role-based LLM routing + proxy + observability** — per-role model routing with per-role cost, local-ready, behind a LiteLLM proxy (Traefik-routed) with a Langfuse observability stack. `scripts/ccr-config.example.json`, infra compose (commits `2fd8d3e`, `36461a3`, 06-10). **(RESOLVED — retroactive)**

---

> **Out of scope of this ledger (engineering-process, not product features):** the Code Knowledge Graph + architecture-drift gate (`29a012e`) and the 5 engineering-core hard gates (`d5e12c1`) — these are CI/process infra, tracked via `.github/workflows/ci.yml` and `smoke/` rather than a product sprint.
