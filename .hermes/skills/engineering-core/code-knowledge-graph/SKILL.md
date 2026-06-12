---
name: code-knowledge-graph
description: Use when mapping a codebase's structure, detecting architecture drift against locked decisions, doing impact analysis before a structural change, or onboarding to an unfamiliar repo - builds a code/architecture knowledge graph (JSON + HTML) and a drift audit
---

# Code Knowledge Graph

A **dev-time** code/architecture knowledge graph (distinct from runtime agent memory like Mem0/Qdrant). Hybrid: a deterministic **static backbone** + graphify-style community clustering + an **architecture-drift audit**, with optional LLM enrichment.

**REQUIRED BACKGROUND:** engineering-core:ground-truth-anchor (the drift audit compares code against `LOCKED-DECISIONS.md`).

## What it produces

`scripts/build_graph.py` (seeded into each project's `codegraph/`) emits to `codegraph/`:
- **graph.json** — nodes (modules · imports · FastAPI endpoints · SQLAlchemy tables · frontend files) + edges (imports/exposes/defines) + directory-based communities.
- **graph.html** — self-contained interactive cytoscape view, colored by community (graphify-style).
- **drift-audit.json** — violations: banned-tech (imports of tech marked REMOVED in `LOCKED-DECISIONS.md`, e.g. pgvector/supabase), frontend→backend layering breaks, and import cycles.

Engine: Python stdlib `ast` (no dep) for the backend; `npx madge` for TS/TSX (skipped gracefully if absent); optional `--enrich` routes a community-summary request through the LiteLLM `role-architect` alias (engineering-core:model-routing).

## When to run

```bash
python codegraph/build_graph.py --backend backend/app --frontend frontend/src \
  --decisions LOCKED-DECISIONS.md --out codegraph [--check] [--enrich]
```

- **Before any structural change** (new module, moved boundary, dependency): regenerate and read `drift-audit.json` — this is how **architecture-guardian** proves the code still matches `LOCKED-DECISIONS.md` and module boundaries.
- **Impact analysis:** trace a node's edges in `graph.json` before changing it.
- **Onboarding:** open `graph.html`.
- **CI drift-gate:** run with `--check` (exits non-zero on ERROR-level drift). Start report-only; flip to blocking once the repo is clean.

## Gate

A structural change is not "done" (engineering-core:verification-before-completion) until the graph regenerates with **no new ERROR-level drift**. A banned-tech import or a frontend→backend layering break is a hard STOP — reconcile the code, or amend `LOCKED-DECISIONS.md` with a dated ADR (never silently drift).
