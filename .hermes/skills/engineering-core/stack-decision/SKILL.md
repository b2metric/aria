---
name: stack-decision
description: Use when choosing or changing the tech stack, or deciding whether to migrate a hot path to Go - records the choice as a dated ADR and owns Go framework/package selection on the user's behalf
---

# Stack Decision

The user is **not** a Go developer. When Go is involved, the agent OWNS the framework/package selection and justifies it — never punt that choice back to the user.

## Defaults (locked unless an ADR supersedes)

- **Phase-1 backend = Python / FastAPI.** Build the product here first. Do not introduce other backend languages speculatively (YAGNI).
- **No Supabase.** Data layer is PostgreSQL 16 (+ Keycloak for auth, alembic for migrations). Never reintroduce Supabase.

## When to migrate a service to Go (NOT before)

Migrate a specific service to Go ONLY when there is **measured** evidence it needs it — not speculation:
- A profiled hot path where Python/FastAPI throughput or tail latency is the proven bottleneck under realistic load, AND
- The service has a stable, narrow contract (good microservice seam), AND
- The win justifies a polyglot operational cost.

If those aren't all true, stay on FastAPI. "It might be slow" is not evidence — measure first (engineering-core:systematic-debugging for the bottleneck).

## When a Go migration IS justified — the agent decides the stack

The user does not know Go, so you choose and justify:
1. Evaluate the current idiomatic Go REST options (stdlib `net/http` + router, or an established framework) against THIS service's needs (routing, middleware, validation, OpenAPI, team-less maintainability). Use engineering-core:writing-plans research step + current docs — do not pick from stale memory.
2. Recommend ONE with a short trade-off rationale and the package set (router, validation, DB driver/ORM, migrations, test framework).
3. Get the human's go/no-go on the migration scope (they approve the WHAT; you own the HOW/which-framework).
4. Record it as a dated ADR row in `LOCKED-DECISIONS.md` (decision, alternatives considered, rationale). It is then settled (engineering-core:ground-truth-anchor).

## Red Flags

| Thought | Reality |
|---------|---------|
| "Let's write this new service in Go to be safe" | No measured bottleneck = stay on FastAPI. YAGNI. |
| "I'll let the user pick the Go framework" | They don't write Go. You own and justify the choice. |
| "Rewrite the whole backend in Go" | Migrate one profiled hot path with a clean seam, not the monolith. |
| "We could also add Supabase for X" | Banned. PostgreSQL + Keycloak only. |
