---
name: aria-docs
description: >-
  Build and refresh ARIA's dual-audience documentation portal (docs-site/, Docusaurus).
  Two pipelines: (1) DEVELOPER docs from source — regenerate the OpenAPI snapshot from the
  running backend and the API reference, plus architecture/config pages synced from
  docs/*.md and backend/app/core/config.py; (2) USER/Academy docs from the live UI — drive
  the running app with Playwright to screenshot each screen and write screen-by-screen MDX
  walkthroughs. Use this whenever backend API, config, or frontend screens change, or when
  (re)generating the docs portal.
---

# aria-docs — ARIA dual-audience documentation

The portal lives in **`docs-site/`** (Docusaurus, two docs instances): **`developers/`**
(technical, source-synced) and **`guide/`** (end-user "Academy", screen-driven). It is a
separate Docusaurus app — do NOT put it under `docs/` (that dir is volume-mounted into the
backend for vault files).

## Build & serve
```bash
cd docs-site
npm install          # first time
npm run start        # dev server (hot reload)
npm run build        # production build — MUST be green (CI gate)
```

## Pipeline 1 — DEVELOPER docs (from source)
Run after any backend API / schema / config change.

1. **Refresh the OpenAPI snapshot** from the running backend (FastAPI auto-emits it):
   ```bash
   curl -s http://api.aria.localhost/openapi.json -o docs-site/static/openapi.json
   ```
   The API reference page (`developers/api.mdx` → Redoc/Scalar reading `/openapi.json`) renders it.
   *(Upgrade path: swap to `docusaurus-plugin-openapi-docs` for native MDX gen if richer per-endpoint
   pages are wanted — Redoc static is the low-risk default.)*
2. **Architecture / config pages** — keep `developers/*.md` synced from the source-of-truth:
   - `developers/architecture.md` ← `docs/technical-architecture.md`, `docs/frontend-architecture.md`, `docs/pipeline-flow.md`
   - `developers/vault.md` ← `docs/vault-schema.md`
   - `developers/config-and-limits.md` ← `backend/app/core/config.py` (row limits, token quotas, BYOK/CMEK), RBAC roles
   - Use the **`update-docs`** skill to diff/sync these from source; **`update-codemaps`** for an architecture map.
3. Never hand-edit generated API pages; edit source + regenerate.

## Pipeline 2 — USER / Academy docs (from the live UI)
Run after any frontend screen change. Produces screenshot + walkthrough per screen.

1. **Bring the stack up** and confirm login works:
   ```bash
   docker compose -f docker-compose.dev.yml up -d        # app at http://aria.localhost
   ```
   Admin screens need Keycloak login (`admin@aria.local` / `admin`).
2. **Capture screenshots** with the existing Playwright harness (reuses `e2e/auth-flow` login):
   ```bash
   cd frontend
   PLAYWRIGHT_NO_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://aria.localhost \
     npx playwright test docs-screenshots
   ```
   PNGs land in `docs-site/guide/_screenshots/<screen>.png`.
3. **Write/refresh the MDX walkthrough** for each screen: embed its screenshot, then explain
   *what the screen does* and *what each control does* (task-based, not technical). Keep the
   brand voice (use `article-writing` + `brand-voice`; `humanizer` to de-stiffen).
4. **Screen inventory** (23) — keep `guide/` in step with these routes:
   `frontend/src/app/`: `chat`, `/` dashboard, `onboarding/{database,sync}`,
   `settings/{general,team,database,encryption}`, `admin/{users,health,memory,team-memory,
   audit-log,tokens,vault-access,tenant-config,llm-config,schema}`, plus `login`, `register`.
   Group in the `guide` sidebar by area: Getting Started · Chat · Onboarding · Settings ·
   Admin · Security & Governance · Analytics & Artifacts.

## Source-of-truth map (do not duplicate — sync)
| Doc page | Source |
|---|---|
| developers/api | backend `/openapi.json` (snapshot in `docs-site/static/openapi.json`) |
| developers/architecture | `docs/technical-architecture.md`, `frontend-architecture.md`, `pipeline-flow.md` |
| developers/vault | `docs/vault-schema.md` |
| developers/config-and-limits | `backend/app/core/config.py`, RBAC roles |
| guide/* | the live screens (screenshots) + existing `docs/academy/*` content |

## Conventions
- Brand palette from `docs/academy/assets/css/style.css` (primary `#2563eb`, Inter / Fira Code) →
  `docs-site/src/css/custom.css`.
- `npm run build` must stay green — it is wired into CI (`docs-build` job) and `smoke/done-check.sh`.
- Screenshots are generated artifacts; regenerate, don't hand-edit. Keep them current after UI changes.
- Public portal: enable `seo` skill on `guide/` pages (meta/description) since end-users reach it.
