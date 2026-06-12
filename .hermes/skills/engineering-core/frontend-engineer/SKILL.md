---
name: frontend-engineer
description: Frontend implementation for ARIA — components, state, data fetching, accessibility. Enforces visual verification and anti-thrash rules.
categories: [devops]
---
# Frontend Engineer — ARIA

Read **`docs/frontend-architecture.md`** FIRST. It is the source of truth for the
component tree, chart rendering, and auth. Do not re-invent the UI.

## Non-negotiable rules (these prevent the page.tsx thrash loop)

1. **VERIFY WITH YOUR EYES.** After any frontend change you MUST render it and look:
   - Ensure dev server is up: `cd frontend && npm run dev` (background).
   - `browser_navigate` to `http://aria.localhost` (and `/chat`), then `browser_screenshots`.
   - Read the screenshot + `browser_console` for errors. Never claim "done" on UI work
     without a screenshot proving it renders. You are vision-capable — use it.
2. **TARGETED PATCHES, NEVER FULL REWRITES.** Edit the specific lines. Do not rewrite
   `chat/page.tsx` (722 lines) or `ChartArea.tsx` wholesale — that reintroduces fixed
   bugs. No `backup_old.tsx` scratch files in the repo root.
3. **ONE WRITER PER FILE.** Never issue parallel/concurrent edits to the same file in
   one turn or across delegated sub-agents — they clobber each other and roll back work.
   Finish one edit, re-read the file, then make the next.
4. **DIAGNOSE BEFORE EDITING.** If the chart "won't show", follow the debug order in
   `docs/frontend-architecture.md`: check backend 200 (Keycloak JWKS!) and response
   shape FIRST. Most "frontend" failures here are backend 500s or a 5 MB Plotly blob —
   not `page.tsx`.

## Charts
- Use `ChartArea` (recharts) with JSON `ChartDataPoint[]` + `ChartConfig`.
- NEVER `doc.write()` multi-MB Plotly HTML into `SafeIframe` — it crashes the React tree.

## General
- Server state vs client state separated; keep the base-UI/API layer swappable.
- Accessible by default (semantic HTML, keyboard, contrast). No `console.log` in committed code.
- Keep sessions scoped; don't run a 200-message marathon on one bug.

## Engineering-core
This IS **engineering-core:frontend-visual-verification** — navigate→screenshot→console→network before done; SafeIframe rejects srcDoc >1MB at runtime; charts from JSON (recharts), not inline Plotly HTML.

## Auth/login changes — REAL verification required (added 2026-06-12)
- The app runs dockerized at **`http://aria.localhost`** (host `frontend/` is bind-mounted → hot-reload). Do NOT start a second `npm run dev`; navigate to `aria.localhost`.
- The default Playwright E2E **mocks** auth (`e2e/utils/auth.ts`) — it does NOT test real login/logout. For ANY auth change, run the real-auth E2E:
  `PLAYWRIGHT_NO_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://aria.localhost E2E_TEST_USER=… E2E_TEST_PASS=… npm run test:e2e:auth`
- NEVER add `app/api/auth/session/route.ts` (shadows NextAuth → bypasses login). Federated logout via `lib/auth.ts keycloakLogout`.
