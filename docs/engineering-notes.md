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
- **Dev login credentials:** username=`admin`, password=`12345`, email=`admin@b2metric.com`.
  (Was `admin@aria.local`, changed for LiteLLM SSO: LiteLLM's strict email validator
  rejects reserved TLDs like `.local`/`.localhost`. Use a real TLD. The realm JSON and
  live Keycloak DB must match — `infra/keycloak/setup-console-sso.py` normalises it.)
- **Embedded Service Consoles SSO:** `/admin/consoles` iframes the infra consoles.
  LiteLLM UI logs in via Keycloak (client `litellm-ui`); run
  `python infra/keycloak/setup-console-sso.py` after a fresh deploy to (re)create the
  OIDC client + mappers. MinIO Community console dropped OpenID SSO upstream
  (RELEASE.2025-09+) → it embeds with native root login only.
- Frontend logout is **federated**: `signOut()` + redirect to Keycloak end-session
  (`id_token_hint` + `post_logout_redirect_uri`), else the SSO cookie silently re-logs in.
  (`post_logout_redirect_uri` = `http://localhost:3003` must be registered on the `aria-web` client.)
- `/chat` redirects unauthenticated users to `signIn("keycloak")`.

## Dockerized stack (Traefik) — `docker-compose.dev.yml` + `infra/traefik-dynamic.yml`
The full stack can run behind Traefik on port 80. macOS `.local` resolution is fraught; we use `.localhost` instead which automatically resolves to loopback on macOS without editing `/etc/hosts` (mostly). Routing:
`aria.localhost`→frontend:3000, `api.aria.localhost`→backend:8000, `auth.aria.localhost`→keycloak:8080.

**The one rule that makes OIDC work: every actor must use the SAME external issuer URL.**
- Traefik has **in-cluster network aliases** (`aria.localhost`, `api.aria.localhost`, `auth.aria.localhost`
  on `aria-net`) so containers resolve those hostnames to Traefik — i.e. the browser AND the
  backend AND next-auth all talk to `http://auth.aria.localhost/auth`. No split-horizon.
- Keycloak: `KC_HOSTNAME: "http://auth.aria.localhost/auth"` (full URL **including `/auth`** — KC26
  builds the issuer from the hostname and does NOT prepend `KC_HTTP_RELATIVE_PATH`),
  `KC_HOSTNAME_STRICT: "false"`, `KC_HTTP_ENABLED: "true"`, `KC_PROXY_HEADERS: "xforwarded"`.
  Resulting issuer: `http://auth.aria.localhost/auth/realms/aria`.
- This exact issuer string must match in frontend `NEXT_PUBLIC_KEYCLOAK_ISSUER`,
  backend `KEYCLOAK_URL=http://auth.aria.localhost/auth`, and the token `iss` claim.
- The `aria-web` client in Keycloak must have `Valid Redirect URIs` and `Web Origins` set to
  `http://aria.localhost/*` (and the next-auth callback `http://aria.localhost/api/auth/callback/keycloak`).
  **Realm changes only apply on re-import** → wipe the volume: `docker volume rm
  b2metric-aria_keycloak_db_data` then `up -d` (dev-only data; no real users).
- **Frontend dev MUST bind `0.0.0.0`** (`command: npm run dev -- -H 0.0.0.0`). Default
  localhost-only bind = Traefik 502. (This was the "broke the UI while dockerizing" bug.)
- Keycloak healthcheck path is **`/auth/health/ready`** on mgmt port 9000 (the relative path
  moves it too); querying `/health/ready` falsely reports `unhealthy`.
- Do NOT re-add a Traefik `hmr-headers` middleware that injects `Connection: Upgrade` on every
  request — it corrupts normal HTML loads. Traefik v3 proxies the HMR websocket natively.

## Frontend chart UX (`frontend/src/app/chat/page.tsx` + `components/ChartArea`, `ChartControls`)
- Claude-Desktop artifact panel: inline collapsible SQL per message, a chart **chip** per
  message that opens the right panel (auto-opens on a new chart; `key={msg.id}` remounts on switch).
- `DataGrid` table view when `chart_config.type === "table"`.
- recharts `ChartArea` renders bar/line/area/pie from `chart_data`.
- **Date-range buttons are data-aware:** derived from the data span (monthly→3M/6M/1Y,
  daily→7d/30d/90d) and **hidden** when the x-axis isn't a date axis.
- **🎨 palette switcher** cycles color palettes client-side.

## Mock Oracle data
- Dev Oracle runs at `localhost:1521/FREEPDB1`. Reseed with
  `python backend/scripts/seed_dummy_data.py` (idempotent).
- **DB Config required:** Each workspace needs a matching row in `customers` +
  `customer_db_configs`. Without this the query pipeline fails. The `oracle` enum value
  must exist in `database_type` — run migrations or `ALTER TYPE database_type ADD VALUE 'oracle'`.

## Running locally (don't break it)
- Backend: `cd ~/projects/b2metric-aria && .venv/bin/uvicorn backend.app.main:app --port 8000 --reload`
- Frontend: `cd frontend && npm run dev -- -p 3003`
- **Never run `next build` while `next dev` is running** — it clobbers `.next` and hangs the dev server.

## Engineering-core operational notes (added 2026-06-11)

- **Real backend ingress is `http://api.aria.localhost`** (Traefik). The `aria-backend` container does NOT publish host `:8000`. If a stale host process squats on `localhost:8000` it may 500 on `/me` — that is NOT the real backend; kill it (`lsof -i :8000`).
- **Smoke gate:** `bash smoke/check.sh` auto-reads `backend/.env` (`KEYCLOAK_URL`/`KEYCLOAK_REALM`/`KEYCLOAK_CLIENT_ID`); login client defaults to the public `aria-web`. Full round-trip: `SMOKE_TEST_USER=<u> SMOKE_TEST_PASS=<p> bash smoke/check.sh`.
- **Keycloak JWKS:** `http://auth.aria.localhost/auth/realms/aria/protocol/openid-connect/certs` (the `/auth` segment is required; resolves in-container too). Token `iss` = `http://auth.aria.localhost/auth/realms/aria` and must match `keycloak_issuer`.
- **LITELLM_API_KEY:** backend now fails loudly at startup if missing/dummy `sk-1234` (`validate_runtime`). Use `ARIA_SKIP_STARTUP_CHECKS=1` only for offline work.
- **Frontend hardcoded fallback trap:** `frontend/src/app/chat/page.tsx` + `api/auth/[...nextauth]/route.ts` carry `http://localhost:8080/auth` fallbacks — if `KEYCLOAK_ISSUER`/`NEXT_PUBLIC_KEYCLOAK_ISSUER` env is unset they hit the wrong host. Keep the env set (dev = `auth.aria.localhost/auth`).

## Frontend auth traps (added 2026-06-12)

- **Rogue `app/api/auth/session/route.ts`** shadows NextAuth's session endpoint and returns `{session}` → `useSession()` reads a truthy object → everyone "authenticated" → dashboard shown without login. Do not create it; NextAuth provides this route.
- **Federated logout** must clear NextAuth (`signOut({redirect:false})`) then `window.location` to the Keycloak end-session URL with `id_token_hint` (helper: `frontend/src/lib/auth.ts`). `signOut({callbackUrl:<cross-origin>})` is silently dropped → SSO persists → silent re-login.
- **`NEXTAUTH_SECRET`** must be set for the frontend (compose) — needs a `docker compose up -d frontend` restart to apply.
- **Frontend dev target = `http://aria.localhost`** (dockerized, host `frontend/` bind-mounted → hot-reload). NOT `localhost:3000`. Do not start a second `npm run dev`.
- **Mocked E2E ≠ real auth.** `e2e/utils/auth.ts` mocks the session; the real flow is only covered by `npm run test:e2e:auth` (real Keycloak). Run it before declaring any auth/login change done.

## LLM Configuration & BYOK (Bring Your Own Key)
- ARIA supports multi-tenant LLM keys (Phase 1). You can set custom keys in the Admin UI (`/admin/llm-config`).
- Queries call `resolve_llm(workspace_id)` before hitting LiteLLM. If no active key is found for the customer, it falls back to the `litellm_api_key` env var.
- DO NOT log API keys in transit. The `ResolvedLLM` class explicitly masks keys in `__repr__`.
