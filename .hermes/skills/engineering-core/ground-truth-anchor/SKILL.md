---
name: ground-truth-anchor
description: Use at session start and after every context compaction in a software project - re-asserts the project root, locked architecture decisions, and invariants before any file-creating action, preventing wrong-repo scaffolding and decision drift
---

# Ground-Truth Anchor

## The Iron Law

**BEFORE ANY FILE-CREATING ACTION, CONFIRM YOU ARE INSIDE THE REGISTERED PROJECT ROOT AND HAVE RE-READ THE LOCKED DECISIONS.**

This gate exists because the agent once **scaffolded code into a throwaway sibling repo** instead of the real project, and **abandoned resolved architecture decisions mid-session** — because aggressive context compression evicted the two most load-bearing facts (the working directory and the resolved decisions), which lived only in conversational scrollback.

## The durable anchor (not scrollback)

Ground truth lives in **files**, never in conversation history (compaction discards history):

- `AGENTS.md` — working-directory lock + working style. Read FIRST, every session.
- `LOCKED-DECISIONS.md` — the resolved-decisions ADR ledger. Each row is settled; do not re-litigate.
- `engineering-notes.md` — known traps and operational truths.

These must be in the profile's pinned/non-compactable context (e.g. referenced from `SOUL.md`, which loads every message).

## The protocol

1. **At session start:** read `AGENTS.md` + `LOCKED-DECISIONS.md`. State the absolute project root you will work in. If the conversation implies a different directory, the files win.
2. **Before every Write / scaffold / `git init` / project-create:** assert the resolved absolute target path is **inside** the registered project root. A path resolving to a sibling (`../<slug>-code`, `../<slug>-new`), `/tmp`, or anywhere outside is a HARD STOP — it is the wrong-repo trap. (A pre-commit hook + write-path guard enforce this in code; this skill is the cognitive layer.)
3. **After any context compaction / "continue from where you left off":** re-read `AGENTS.md` + `LOCKED-DECISIONS.md` before acting. Do not trust your in-context memory of the root or the decisions — re-anchor from the files.
4. **When tempted to change a settled decision:** a locked decision (e.g. "Mem0+Qdrant for memory", "no ClickHouse in Phase 1", "PostgreSQL not Supabase") is NOT re-openable mid-task. If a change is truly needed, surface it explicitly to the human and amend `LOCKED-DECISIONS.md` with a new dated ADR row — never silently drift.
5. **New architectural decision reached:** append it to `LOCKED-DECISIONS.md` (dated) so it survives the next compaction.

## Red Flags

| Thought | Reality |
|---------|---------|
| "I'll just scaffold a clean repo over here" | Wrong-repo trap. Work inside the registered root only. |
| "I think the decision was X" | Don't think — re-read LOCKED-DECISIONS.md. |
| "Compaction happened, but I remember the setup" | Compaction drops load-bearing facts. Re-anchor from files. |
| "This decision seems wrong, I'll just change it" | Locked = settled. Surface + amend the ADR, don't drift. |
