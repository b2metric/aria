---
name: model-routing
description: Use when dispatching an engineering subagent or choosing which model serves a role - maps each role to the right model tier (reasoning / cheap-fast / vision) and enforces reviewer-must-differ-from-author
---

# Model Routing (hybrid local + cloud)

**Flexible skill** — adapt the specific model per availability, but the TIER logic and the reviewer-diversity invariant are rigid.

Every model call goes through the LiteLLM proxy, which exposes per-role aliases. Pick the role; the proxy resolves it to a cloud primary and a local (vLLM) option with fallbacks. See `infra/llm/config.yaml` and `infra/llm/RUNBOOK-local-serving.md`.

## Principles

1. **Reasoning tier** (extended thinking) for work where a wrong early step is expensive: architecture, planning/brainstorming, systematic debugging, final review. Spend tokens here.
2. **Cheap-fast tier** for high-volume, lower-complexity work: bulk codegen, QA/smoke parsing, boilerplate. Never burn reasoning-tier tokens on green test logs.
3. **Vision tier** ONLY where a screenshot must be interpreted: frontend visual verification. Text-only coders cannot verify pixels.
4. **Reviewer ≠ author** (rigid): a model is blind to its own characteristic mistakes. The code reviewer MUST be a different model family than the author. This is a routing invariant, not a prompt suggestion.
5. **Local-first for cost/privacy** on high-volume roles when the local GPU is up; **cloud for the reasoning tier**, hard vision, and burst. Hybrid by design — fallbacks cross the local↔cloud boundary so a cloud-credit-exhaustion or a stalled local endpoint routes onward transparently.

## Role → tier → alias

| Role | Tier | Request alias |
|------|------|---------------|
| Architect / planner / brainstorming | reasoning | `role-architect` |
| Lead dev / writing-plans | mid | `role-lead-dev` |
| Backend codegen / bulk | cheap-fast | `role-backend-codegen`, `role-bulk-worker` |
| Frontend (build + screenshot verify) | mid + vision | `role-frontend-vision` |
| Systematic debugger / root-cause | reasoning | `role-debugger` |
| Code reviewer (≠ author) | reasoning, foreign family | `role-reviewer` + `review-of-<author-family>` |
| QA / smoke / verification gate | cheap-fast | `role-qa-gate` |

## Reviewer diversity

When dispatching review, the orchestrator passes the **author's family**; the proxy routes to a `review-of-<family>` alias whose fallback chain contains ONLY foreign families (author=Claude → reviewer Gemini/DeepSeek; author=Qwen-local → reviewer GLM/Claude). Never let a family grade its own homework. Pairs with engineering-core:requesting-code-review and the santa-loop dual-review pattern.

## Cost

Every alias carries `input_cost_per_token`/`output_cost_per_token` (local = 0), and every request is tagged `metadata: {agent_role, author_family}` so Langfuse/LiteLLM attribute spend per role. If a role's cost is showing as $0, the alias is missing cost config — fix it.
