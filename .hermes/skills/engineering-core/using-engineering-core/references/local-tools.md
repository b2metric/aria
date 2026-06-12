# Engineering-core tool mapping — local model (vLLM / OpenAI-compatible)

When a worker runs on a **local model** served by vLLM behind the LiteLLM proxy, the harness has no native skill/subagent/todo tools. The controller (Hermes or Claude Code) supplies them; the local model just needs the content in its context.

| Capability | Local-model approach |
|------------|----------------------|
| Load a skill | The controller pastes the skill body (and any REQUIRED SUB-SKILL bodies) directly into the worker's prompt. Reference skills by bare `name`; the controller resolves and inlines them. |
| Dispatch a subagent | The controller makes a fresh OpenAI `chat/completions` call with a curated, isolated context (no shared history). Tool-calling uses the model's native function-calling (GLM `glm45` / Qwen `qwen3_coder` parsers). |
| Track todos | The controller maintains the checklist (Kanban card / TodoWrite) out-of-band; the local model just executes the current step. |
| Vision (screenshot verify) | Route to the vision alias (`role-frontend-vision` → local Qwen3-VL or cloud Gemini). The coder MoE and the VLM cannot co-reside on one 96 GB card — they alternate (see RUNBOOK-local-serving.md), so visual checks are discrete steps. |

## What still applies unchanged

The DISCIPLINE is model-agnostic: TDD's iron law, systematic-debugging's phases + fix-count gate, verification-before-completion, the smoke gate, and ground-truth-anchor all work identically on a local model. Only the tool *names* differ; the gates do not relax for a cheaper model.

## Caveat

Local models vary in tool-call reliability. For tool-call-heavy agentic loops prefer the strongest local coder (e.g. GLM-4.5-Air, ~90% tool-call success) or fall back to cloud (engineering-core:model-routing). If a local model loops or drops tool calls, the routing fallback escalates to cloud.
