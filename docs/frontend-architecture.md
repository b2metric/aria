# ARIA — Frontend Architecture

> **Stable anchor.** Read this before touching `frontend/`. It documents what EXISTS
> so the agent stops re-inventing the UI every session. If you change the structure,
> update THIS file in the same commit.

## Stack
- Next.js 16 (App Router) + React, TypeScript, Tailwind, **recharts** for charts.
- Dev server: `cd frontend && npm run dev` → **http://localhost:3000**.
- Backend API base: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Component tree (source of truth — file : role)
```
src/app/
  layout.tsx            Root layout (AuthProvider wrapper)
  page.tsx (159)        Dashboard landing (stats, recent, saved queries)
  chat/page.tsx (722)   ★ Main chat UI — query input, SSE stream, chart+SQL preview.
  chat/layout.tsx       Chat route layout
  api/auth/[...nextauth]/route.ts   next-auth route
src/components/
  ChartArea.tsx (321)   ★ Chart renderer — recharts (bar/line/area/pie) from JSON data
  ChartControls.tsx     Chart type/filter/zoom/export controls
  SafeIframe.tsx (24)   Iframe that doc.write()s raw HTML  ← see "Charts" warning below
  AuthProvider.tsx      next-auth SessionProvider wrapper
  Sidebar / RecentConversations / SavedQueries / QuerySearch / StatCard
src/lib/
  api.ts (251)          API client: streamQuery (SSE), fetchConversations, dashboard
  types.ts (96)         ChartConfig, ChartDataPoint, DashboardData, FilterState
```
`chat/page.tsx` and `ChartArea.tsx` are the two files that get thrashed — treat them
as the high-risk surface. Make targeted edits, never full rewrites.

## Charts — THE rule (this is what keeps breaking)
- **Render charts with `ChartArea` (recharts) from JSON data points** (`ChartDataPoint[]`
  + `ChartConfig`). This is the correct, working path.
- **DO NOT** push backend-rendered Plotly HTML (often ~5 MB inline) into `SafeIframe`
  via `doc.write()`. That synchronously blocks the main thread and crashes the React
  tree ("ekran siliniyor"). The backend should return a **chart spec / data points
  (JSON)**, and the frontend renders with recharts.
- If a raw HTML/Plotly artifact must be shown, lazy-load it in a sandboxed iframe via
  `src` (a URL to the MinIO artifact), never `srcDoc`/`doc.write` of multi-MB strings.

## Auth (currently mixed — a known bug source)
- Two mechanisms coexist: **next-auth** (`AuthProvider`, `getSession`) AND a **manual
  bearer token** read from `localStorage.aria_access_token` / cookie `aria_token`
  (`api.ts`). Pick ONE; the manual-token path is what `streamQuery`/`fetchConversations`
  actually use. Don't add a third.
- Backend verifies via **Keycloak JWKS**. Correct realm cert URL is
  `http://localhost:8080/realms/aria/protocol/openid-connect/certs`
  (Keycloak ≥ 18 dropped the `/auth` prefix). A wrong `KEYCLOAK_URL` (trailing `/auth`)
  is the cause of the recurring backend **500s** on `/api/conversations` and `/api/query`.

## TARGET UX — Claude-Desktop-style conversation + artifact panel (the goal)

This is the intended design. Build toward it; do NOT redesign it each session.

- **Main column = the conversation.** Each assistant message renders, in order:
  1. prose/insight text,
  2. **SQL inline, inside the message** as a collapsible code block (visible to
     admin / SQL-permitted roles only — others see the answer, not the SQL string),
  3. one **artifact chip** per chart, e.g. `📊 Bar chart — Revenue by region`.
- **Artifact chip → right panel.** Clicking a chip opens the **right-side Artifact
  Panel** showing THAT message's artifact. When a new chart streams in, the panel
  **auto-opens** on that artifact (first-render). The panel is closable and is keyed
  to a single `activeArtifactMsgId` — not the global "latest" only.
- The data model already supports this: `ChatMessage` carries `sql`, `chartSpec`,
  `chartHtml`, `chartUrl` per message (see the history mapper in `chat/page.tsx`).
  So this is a RENDER change, not a data change.

### Concrete changes (targeted, in `chat/page.tsx`)
- Add state `activeArtifactMsgId: string | null` (replaces the global
  `sqlPreview`/`currentChart`/`chartHtml`/`chartUrl` panel coupling).
- In the message map: render `msg.sql` inline (code block) and, if the message has a
  chart, render a chip `<button onClick={() => setActiveArtifactMsgId(msg.id)}>`.
- On the `chart` SSE event, also `setActiveArtifactMsgId(assistantMsg.id)` so it
  auto-opens.
- Right panel renders the artifact of the message whose id === `activeArtifactMsgId`,
  using `ChartArea` (recharts) for `chartSpec`; close button sets it back to null.
- Old "SQL Preview" right panel (lines ~657-719) is replaced by this generic panel.

## Data flow
`chat/page.tsx` → `streamQuery()` POST `/api/query` (SSE) → stream chunks (text +
chart spec) → render text in chat, chart via `ChartArea`. History via
`/api/conversations`. Mock fallback in `api.ts` (`getMockDashboardData`) when backend down.

## When the chart "won't show" — debug order (don't rewrite page.tsx first)
1. Is the **backend up and 200**? `curl -s localhost:8000/api/conversations -H "Authorization: Bearer <t>"`. 500 → Keycloak JWKS URL (above), not the frontend.
2. Is the response a **JSON chart spec** or a giant HTML blob? If HTML → fix the backend to return data points; don't iframe it.
3. Only then touch `ChartArea`/`page.tsx`, with a **targeted patch**, and **verify visually** (screenshot localhost:3000) before claiming done.

## SafeIframe runtime guard (added 2026-06-11)

`SafeIframe.tsx` now **refuses `srcDocContent` > 1 MB** at runtime (renders a notice instead of `doc.write`) — the code-level guard against the ~5 MB inline-Plotly blob that crashed the React tree. Charts must render from JSON (`chart_data`) via recharts, never inline multi-MB HTML. Enforced by engineering-core:frontend-visual-verification.
