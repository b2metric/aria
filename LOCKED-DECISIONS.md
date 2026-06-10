# LOCKED-DECISIONS.md — ARIA (Conversational BI)

> The ADR ground-truth ledger (engineering-core:ground-truth-anchor). Each row is a
> SETTLED decision — do NOT re-litigate mid-task. To change one: STOP, surface it to the
> human, add a NEW dated row that supersedes the old. Lives on disk so it survives
> context compaction. Mirrors / supersedes the table in AGENTS.md §2.

## Resolved decisions

| # | Date | Decision | Locked resolution |
|---|------|----------|-------------------|
| 1 | 2026-06-08 | Long-term memory | Mem0 + **Qdrant** (pgvector REMOVED) |
| 2 | 2026-06-08 | Sandbox execution | Flag-only (prod perf) |
| 3 | 2026-06-08 | Ollama | Optional, NOT default |
| 4 | 2026-06-08 | ClickHouse | **Phase 3** only |
| 5 | 2026-06-08 | Go microservice | REMOVED (revisit only for a measured hot path post-MVP — engineering-core:stack-decision) |
| 6 | 2026-06-08 | Token refresh | Silent refresh |
| 7 | 2026-06-08 | Reverse proxy | **Traefik 3** (nginx NOT used) |
| 8 | 2026-06-08 | Teams / PowerBI | **Post-MVP** |
| 9 | 2026-06-10 | Backend stack | Python / FastAPI; PostgreSQL 16 + alembic; Keycloak auth. **No Supabase.** |
| 10 | 2026-06-10 | LLM routing | LiteLLM proxy, per-role aliases, hybrid local+cloud, reviewer != author (engineering-core:model-routing) |
| 11 | 2026-06-10 | Chart payload | JSON `chart_data` → recharts. NEVER inline multi-MB HTML via doc.write (SafeIframe rejects >1 MB) |
| 12 | 2026-06-10 | Auth JWKS | Keycloak `KC_HTTP_RELATIVE_PATH=/auth`; JWKS at `…/auth/realms/aria/protocol/openid-connect/certs`. Backend fails loudly at startup if unreachable. |

## Hard product invariants (see AGENTS.md §3 — honor exactly)
User↔Team 1–1 · SQL visible only to admin/SQL roles · per-query row limit (admin-only) ·
daily token cap per user/team/session · backup-before-delete to MinIO JSON · never auto-delete
users/memory_entries · pipeline NL2SQL→Chart→Insight→Suggestions · base-UI API stays swappable.
