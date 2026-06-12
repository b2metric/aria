# Engineering-core tool mapping — Hermes runtime

Engineering-core skill bodies are written in Claude Code tool names. On the **Hermes** agent framework, map them as follows.

| Claude Code | Hermes equivalent |
|-------------|-------------------|
| `Skill` tool (invoke a skill) | Skills are given to a worker via the `--skill <name>` flag (kanban task) or named in the `delegate_task` context. The bootstrap `using-engineering-core` is auto-loaded every message via the profile `SOUL.md`. |
| `Task` (dispatch a subagent) | `delegate_task(goal=..., context=..., toolsets=[...])`. Subagents have NO memory — paste the FULL task text + scene-setting context into `context` (never make them read the plan file). |
| Parallel `Task(...)` calls | `delegate_task(tasks=[{...}, {...}])` — but never run two implementers on the same file. |
| `TodoWrite` | The Kanban board IS the todo list — create one card per checklist item; the dispatcher claims and spawns them. |
| `EnterPlanMode` / native worktree tool | Hermes has no native worktree tool — `using-git-worktrees` falls through to the `git worktree add` path (Step 1b). |
| `SessionStart` hook injection | Not available — the `SOUL.md` per-message load is the Hermes equivalent bootstrap mechanism. |

## Subagent-driven development on Hermes

The two-stage review (spec-compliance → code-quality) maps to two sequential `delegate_task` calls after the implementer's `delegate_task`. The reviewer's `context` must include the author's model family so the orchestrator can route it to a **different** family (engineering-core:model-routing). Distrust the implementer's report — the reviewer reads the actual code/diff.

## Model selection

Each role's task should set its model via the LiteLLM `role-*` alias (engineering-core:model-routing). In Hermes config this is the worker profile's `model.default` or a per-task model override resolving to a `role-*` proxy alias.
