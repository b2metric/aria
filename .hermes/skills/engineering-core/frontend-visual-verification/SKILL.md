---
name: frontend-visual-verification
description: Use before declaring ANY frontend/UI change complete - requires rendering the running app in a real browser and observing screenshot + console + network before done, never editing the UI blind
---

# Frontend Visual Verification

**REQUIRED BACKGROUND:** engineering-core:verification-before-completion. This skill is the UI instance of it.

## The Iron Law

**NO UI CHANGE IS DONE UNTIL YOU HAVE SEEN IT RENDER AND READ THE CONSOLE.**

Editing a `.tsx` file is not progress. "It looks right in the code" is not evidence. You must observe the running UI.

This gate exists because the frontend was once developed **blind** — the profile had no browser tool and blocked localhost, so the agent edited one page **35 times by guessing**, did full-file rewrites, and never saw that the real defect was a backend bug plus a **5 MB inline Plotly HTML injected via `doc.write()` into an iframe that crashed React**. None of that is visible without a browser.

## Prerequisites (must be true in the profile/config)

- A browser tool is available (Claude Preview / Playwright / Claude-in-Chrome / browser MCP).
- Private/localhost URLs are allowlisted (`allow_private_urls: true`). If you cannot reach `localhost:<port>`, STOP and fix the config first — do not proceed blind.

## The Gate (run in order)

1. **Ensure the app is running** and the change is deployed to the dev server.
2. **Navigate** to the affected route in the browser.
3. **Screenshot** it (and the relevant breakpoints — 320 / 768 / 1024 / 1440 for layout-affecting changes).
4. **Read the browser console** — assert ZERO errors (warnings noted). A console error means NOT done.
5. **Read the network panel** — assert the data calls the page depends on returned `200` with the expected shape. A blank chart is usually a backend `4xx/5xx` or wrong payload, not a frontend bug.
6. **Assert the target element is actually visible** and renders the intended content (not a spinner, not an error boundary, not empty).
7. **Attach the screenshot + console summary** as the completion evidence.

## Anti-thrash circuit-breaker (HARD)

If you have edited the **same file more than 3 times** without a successful render-and-observe in between: **STOP**. You are guessing. Switch to engineering-core:systematic-debugging and engineering-core:frontend-visual-verification:
- Diagnose the **backend first** (is the API returning 200 with the right shape?).
- Trace the real failing layer before touching the component again.
- Prefer **targeted edits** over full-file rewrites.
- One writer per file — never run parallel edits on the same component.

## Hard component rules (this project's traps)

- **Never** inject multi-megabyte HTML via `doc.write()` into an iframe — it crashes React. Charts render from JSON data (`chart_data` → recharts), not inline Plotly HTML. A runtime guard rejects `srcDoc` > 1 MB.
- No scratch files (`backup_old.tsx`, `diff.txt`) at the repo root.

## Red Flags

| Thought | Reality |
|---------|---------|
| "The JSX looks correct" | You haven't rendered it. Screenshot or it isn't done. |
| "It probably renders fine" | Probably = unverified. Navigate and look. |
| "Let me just try another edit" | 3+ blind edits = STOP. Debug the backend/data first. |
| "I'll rewrite the whole component" | Rewrites lose working code. Make a targeted edit. |
