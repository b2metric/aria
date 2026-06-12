# engineering-core

The portable software-engineering discipline pack for the Hermes toolkit. Loaded **only** into software/product (CODE) contexts — never into GTM/business contexts.

Adapted from the MIT-licensed [obra/superpowers](https://github.com/obra/superpowers) (v5.1.0). See `ATTRIBUTION-superpowers-LICENSE.txt`. Cross-skill references are namespaced `engineering-core:<name>`; descriptions are triggers-only (CSO); skills reference each other by name, never via `@`-links.

## Entry point

`using-engineering-core` is the bootstrap — auto-loaded every message (Hermes `SOUL.md` / Claude Code `SessionStart`). It forces a skill-check before any action and defines the pipeline + the non-negotiable gates.

## The pipeline

```
brainstorming → using-git-worktrees → writing-plans
  → subagent-driven-development (or executing-plans) → test-driven-development
  → requesting-code-review (reviewer ≠ author) → smoke-gate → finishing-a-development-branch
```

## Skills

**Vendored from superpowers (discipline kept verbatim, wiring adapted):**
brainstorming · writing-plans · executing-plans · subagent-driven-development · dispatching-parallel-agents · test-driven-development · systematic-debugging (+ root-cause-tracing, defense-in-depth, condition-based-waiting) · requesting-code-review · receiving-code-review · using-git-worktrees · finishing-a-development-branch · verification-before-completion · writing-skills · using-engineering-core (bootstrap).

**This toolkit's additions (hard gates born from real failures):**
- `ground-truth-anchor` — survive compaction; no wrong-repo scaffolding or decision drift.
- `smoke-gate` — boot + real login must round-trip before done.
- `frontend-visual-verification` — render + screenshot + console before any UI done; anti-thrash circuit-breaker.
- `model-routing` — role→tier→alias; reviewer ≠ author; hybrid local+cloud.
- `stack-decision` — Python/FastAPI first, Go only when measured; the agent owns Go framework choice.
- `code-knowledge-graph` — dev-time code/architecture graph (JSON+HTML) + drift audit (code vs LOCKED-DECISIONS); powers architecture-guardian + a CI drift-gate.

## Portability

`using-engineering-core/references/` maps Claude Code tool names to Hermes (`hermes-tools.md`), local vLLM models (`local-tools.md`), and Codex/Gemini/Copilot (vendored `*-tools.md`).
