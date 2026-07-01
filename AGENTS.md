# AGENTS.md — ARIA grounding & guardrails

> Read this FIRST, every session, before any tool call. It is short on purpose.
> It exists because earlier agent runs drifted (lost the working dir, re-decided
> settled questions, scaffolded into a throwaway repo). These rules are immune to
> context compression because they live on disk — re-read them, don't rely on memory.

## 0. Working directory — the prime directive

- **You work in `/Users/tunasonmez/projects/b2metric-aria`. This IS the project.**
- **NEVER** create a new repo, clone into a sibling folder (`*-code`, `*-new`), or
  scaffold into a temp dir. If code "isn't visible", it belongs HERE — `cd` here.
- The GitHub remote for this repo is `b2metric/aria`. Push from this folder only.

## 1. Source of truth

- Architecture authority: **`docs/technical-architecture.md`** (v2.0, decisions resolved).
- **Operational truth & gotchas: `docs/engineering-notes.md`** — read before debugging
  wrong-SQL / blank-chart / 401 / broken-pipe. Covers the LiteLLM key requirement,
  the restyle fast-path, the JSON chart payload, Keycloak `/auth`, the dummy-data
  seeder, and how to run the app locally.
- **Frontend authority: `docs/frontend-architecture.md`** — read before touching
  `frontend/`. Frontend work MUST be verified visually (render `http://aria.localhost`
  via Traefik + `browser_screenshots`; `:3000` is only the internal container port, not
  the host URL); edit with targeted patches, one writer per file. The chart
  UI is `ChartArea` (recharts), NOT 5 MB Plotly HTML in an iframe.
- Per-task design reviews: **`docs/reviews/*.md`**.
- **Code vs business split:** this repo is CODE only. GTM / market research /
  product strategy live in the sibling `b2metric-aria-gtm` profile at
  `~/projects/b2metric-aria-gtm` — don't recreate `gtm-strategy.md`,
  `market-research.md`, `product-design.md`, or wireframes here.
- If a request conflicts with a Resolved Decision below, STOP and ask — do not
  silently re-architect.

## 2. Resolved decisions — do NOT re-litigate

| # | Decision | Locked resolution |
|---|----------|-------------------|
| 1 | Long-term memory | Mem0 + **Qdrant** (pgvector REMOVED) |
| 2 | Sandbox execution | Flag-only (prod perf) |
| 3 | Ollama | Optional, **NOT** default |
| 4 | ClickHouse | **Phase 3** only |
| 5 | Go microservice | REMOVED |
| 6 | Token refresh | Silent refresh |
| 7 | Reverse proxy | **Traefik 3** (nginx is NOT used) |
| 8 | Teams / PowerBI | **Post-MVP** — do not build in MVP |

## 3. Hard product invariants (user-corrected repeatedly — honor them)

- **User ↔ Team is 1–1.** Each user belongs to exactly one team/department/group.
- **SQL visibility:** the SQL query string and raw SQL result are visible ONLY to
  admin / SQL-permitted roles. Everyone else sees the answer + chart, never the SQL.
- **Row-count limit:** there is a per-query row limit. Only **admin** can change it.
  Requests above the limit produce a high-row report whose **MinIO link is stored
  and logged in artifacts** (not inlined in chat).
- **Token limits:** daily token cap per **user, per team, per session** — counted
  even for local/Ollama models. Only **admin** can change the cap.
- **Backup-before-delete:** `customers`, `token_usage_daily`, `queries`,
  `background_jobs` must be backed up to **MinIO as JSON** before any deletion.
- **Never auto-delete** `users` or `memory_entries` — admin deletes manually from
  the UI; this is institutional know-how and must not be lost.
- **Response pipeline:** NL2SQL → Chart → Insight (humanized explanation) →
  Next-step Suggestions (uses data + user memory + team memory).
- **Frontend base-ui API must stay swappable.**

## 4. Working style (anti-drift)

- Keep sessions scoped and short. Finish one slice, verify, then start the next —
  do not run 100+ turns on autopilot.
- Before claiming "done", run the build/tests and paste the real output.
- When you make a new architectural choice, append it to
  `docs/technical-architecture.md` so it survives the next session.

## 5. Discipline (Claude Code — migrated off Hermes 2026-06-14)

- **Ground truth: `LOCKED-DECISIONS.md`** (ADR ledger) — read alongside this file; never re-litigate a locked row.
- **Hard gates** (mechanical, harness-independent — no "done" without them): boot+login smoke (`bash smoke/check.sh`), full Definition-of-Done (`bash smoke/done-check.sh` = BE+FE+tests+smoke), backend startup validation (`validate_runtime`), `SafeIframe` >1 MB guard, `.githooks/pre-commit` (TDD + path/secret guard), CI (`.github/workflows/ci.yml`, blocking). Cite run-evidence before claiming done.
- **LLM calls** route via the LiteLLM proxy (`infra/llm/config.yaml`); **reviewer ≠ author**. Stack: Python/FastAPI → Go only when measured.
- **Agent harness: Claude Code** (was Hermes). Discipline = **`CLAUDE.md`** + skills (superpowers + everything-claude-code) + the mechanical gates above. Models via claude-code-router → LiteLLM (see `CLAUDE.md` §2).
