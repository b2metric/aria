# CLAUDE.md — ARIA (Claude Code grounding)

> Read FIRST, every session. Short on purpose. Ground truth lives on disk so it survives
> context compression. (Migrated off Hermes → Claude Code, 2026-06-14.)

## 0. Working directory — prime directive
- You work in `/Users/tunasonmez/projects/b2metric-aria`. This IS the project.
- **NEVER** create a new repo, scaffold into a sibling/temp dir, or clone elsewhere. If code
  "isn't visible", it belongs HERE — `cd` here. Remote: `b2metric/aria` (push from here only).

## 1. Ground truth (read before acting)
- **`AGENTS.md`** — resolved decisions + hard product invariants (RBAC, SQL visibility, row
  limits, token quotas, backup-before-delete, user↔team 1–1). Do not re-litigate; if a request
  conflicts, STOP and ask.
- **`LOCKED-DECISIONS.md`** — locked architecture (Mem0+Qdrant, Traefik, no Supabase/pgvector…).
- **`docs/technical-architecture.md`** (authority) · **`docs/engineering-notes.md`** (gotchas:
  LiteLLM key, Keycloak `/auth`, `.localhost` routing, how to run locally) ·
  **`docs/frontend-architecture.md`** (FE authority — chart UI is `ChartArea`/recharts).
- GTM/market/product-strategy live in the sibling `b2metric-aria-gtm` profile — not here.

## 2. Models (Claude Code → your own LLMs, no Anthropic billing)
Claude Code is driven through **claude-code-router → LiteLLM proxy (`localhost:4000`)** using
YOUR Gemini/DeepSeek tokens (see `scripts/ccr-config.example.json`, launch with `ccr code`):
- **Orchestrator / tool-loop / vision:** `gemini-reasoner` (gemini-3.1-pro, ~1M ctx, vision).
- **Deep reasoning / review:** `deepseek-reasoner` (DeepSeek-R1) — reviewer ≠ author.
- **Bulk/leaf codegen:** `deepseek` (cheap).
- **Vision (screenshots) MUST go to gemini** — R1 is text-only. Flip to `claude-sonnet` if
  Anthropic billing is funded.

## 3. Discipline (skills)
Use the installed skill packs — **superpowers** (disciplined pipeline) + **everything-claude-code**
(tdd-workflow, verification-loop, quality-gate, code-review, frontend-patterns, e2e-testing,
browser-qa, hookify). Pipeline for any build:
`brainstorm → writing-plans → TDD (test first) → subagent-driven-development → code-review
(reviewer ≠ author) → smoke`. Invoke the relevant skill BEFORE acting.

## 4. Mechanical gates (harness-independent — the real safety net)
These hold regardless of model and run automatically:
- **`smoke/done-check.sh`** — run before ANY "done": backend tests + frontend tests + an API
  must have a UI surface + boot/login smoke. **Done = BE + FE + tests + smoke**, with cited evidence.
- **`.githooks/pre-commit`** — TDD guard (backend logic change needs a test; `SKIP_TDD_GUARD=1` to bypass) + secret/scratch/path guards.
- **CI** (`.github/workflows/ci.yml`) — backend pytest is BLOCKING, frontend tests, smoke-boot, codegraph drift.
- **`bash smoke/check.sh`** — boot + Keycloak login round-trip.
- **Frontend is NOT optional:** an API with no UI is INCOMPLETE. Verify UI visually (render
  `aria.localhost` via Playwright/Chrome MCP + screenshot); never edit the FE blind.

## 5. Hard rules
- Vertical slices, not layers: each feature = tests-first + backend + Next.js FE surface + visual-verify + green smoke.
- No "done" without run-evidence (exit codes / test output / screenshot).
- Immutable/locked decisions in `LOCKED-DECISIONS.md` are not re-opened.
