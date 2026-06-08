# Engineering Notes — operational truth & gotchas

> Read this before debugging "wrong SQL / blank chart / 401 / broken pipe". It records
> how the system ACTUALLY behaves and the traps that already bit us. Keep it current.

## NL2SQL / LLM (the #1 source of "wrong query")
- SQL is generated in `backend/app/query/pipeline.py::_generate_sql`. Low keyword-score
  questions delegate to `llm_sql.generate_sql_with_llm` (LiteLLM proxy on :4000).
- **The backend's LiteLLM key must be VALID.** `backend/.env` `LITELLM_API_KEY` must be a
  working proxy key (the LiteLLM **master key** from `core/hermes-llm-infra/.env`). A stale
  key → every LLM call returns **401** → SQL silently falls back to a dumb rule-based guess
  (e.g. `SUM(OFFER_ID) FROM dim_prep_products`). Verify: `curl :4000/v1/models -H "Authorization: Bearer <key>"` must return 200.
- **Conversation-aware follow-ups:** `process_query` passes recent history (prior questions +
  the SQL used) into the LLM prompt, so "filter to last 30 days" / "add region" modify the
  previous query instead of starting over.
- **Only real tables.** The prompt forbids inventing tables and prefers FACT tables (`fct_*`)
  for metrics; `dim_*` only via JOIN. (Picking a non-existent table → ORA-00942.)

## Deterministic "restyle" fast-path (no SQL)
`process_query` short-circuits BEFORE SQL when the message is a pure presentation change and
a previous result with `chart_data` exists — it reuses that data, never re-runs SQL:
- **Chart type:** "give me a pie chart", "make it a bar", "as line".
- **Data grid:** "give me data grid", "show as table" → `chart_config.type = "table"`.
- **Color palette:** "change color palette", "renkleri değiştir" → rotates `chart_config.colors`.
Detection: `_detect_requested_chart_type`, `_is_chart_type_only_request`, `_wants_color_change`.

## Chart payload (never ship 5 MB again)
- `_build_chart` returns `chart_data` (JSON rows, capped 1000) + `chart_config`
  `{type, title, xKey, yKeys, colors, ...}` + `chart_url` (MinIO link). It does **NOT** stream
  the inline Plotly HTML (~4.85 MB) — that crashed the SSE stream / React tree.
- All values are JSON-safe coerced (Decimal→float, datetime/date→isoformat); SSE `json.dumps`
  also uses `default=str`. Empty result → `chart_data: []` (no KeyError).

## Auth / Keycloak
- Keycloak 26 runs with `KC_HTTP_RELATIVE_PATH=/auth`, so JWKS lives at
  `http://localhost:8080/auth/realms/aria/protocol/openid-connect/certs`.
  `backend/.env` `KEYCLOAK_URL` **must include `/auth`** (do NOT "fix" by removing it).
- Frontend logout is **federated**: `signOut()` + redirect to Keycloak end-session
  (`id_token_hint` + `post_logout_redirect_uri`), else the SSO cookie silently re-logs in.
  (`post_logout_redirect_uri` = `http://localhost:3003` must be registered on the `aria-web` client.)
- `/chat` redirects unauthenticated users to `signIn("keycloak")`.

## Frontend chart UX (`frontend/src/app/chat/page.tsx` + `components/ChartArea`, `ChartControls`)
- Claude-Desktop artifact panel: inline collapsible SQL per message, a chart **chip** per
  message that opens the right panel (auto-opens on a new chart; `key={msg.id}` remounts on switch).
- `DataGrid` table view when `chart_config.type === "table"`.
- recharts `ChartArea` renders bar/line/area/pie from `chart_data`.
- **Date-range buttons are data-aware:** derived from the data span (monthly→3M/6M/1Y,
  daily→7d/30d/90d) and **hidden** when the x-axis isn't a date axis.
- **🎨 palette switcher** cycles color palettes client-side.

## Mock Oracle data
- The vault documents 9 tables but the mock Oracle (`stc/stc123@localhost:1521/FREEPDB1`,
  schema STC) originally had only `fct_prep_master` + `fct_prep_rev` (4 rows each) → the LLM
  often picked non-existent tables.
- **Reseed:** `python backend/scripts/seed_dummy_data.py` creates any missing vault table and
  fills all 9 with JOIN-consistent, multi-month, multi-nationality dummy data (idempotent).

## Running locally (don't break it)
- Backend: `cd ~/projects/b2metric-aria && .venv/bin/uvicorn backend.app.main:app --port 8000 --reload`
- Frontend: `cd frontend && npm run dev -- -p 3003`
- **Never run `next build` while `next dev` is running** — it clobbers `.next` and hangs the dev server.
