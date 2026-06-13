# smoke/ — boot + login gate (engineering-core:smoke-gate)

The BLOCKING completion gate. Proves the stack boots and a real login round-trips
before any "done"/deploy. Catches the two classes that shipped silently:
"system down" and "up-but-can't-login" (the Keycloak JWKS `/auth` path trap).

## Run

```bash
# health + JWKS-path assertion (no creds needed):
bash smoke/check.sh

# full login round-trip (set creds for a seeded test user + a direct-access client):
SMOKE_TEST_USER=alice SMOKE_TEST_PASS=... SMOKE_CLIENT_ID=aria-frontend \
  bash smoke/check.sh
```

Env (defaults target local dev): `SMOKE_BACKEND_URL` (http://localhost:8000),
`SMOKE_KEYCLOAK_URL` (http://localhost:8080/auth), `SMOKE_REALM` (aria),
`SMOKE_TEST_USER` / `SMOKE_TEST_PASS` / `SMOKE_CLIENT_ID` (enable the login step),
`SMOKE_CLIENT_SECRET` (if the client is confidential).

Exit non-zero on any failed gate. Wired into CI (`.github/workflows/ci.yml`).

## Profile audit (Hermes factory contract)

`verify-profile.sh` audits THIS project's Hermes profile against the Project
Factory v4 contract — config-as-code symlinks, engineering-core, role + toolkit
skills present AND curator-pinned, consumer bloat pruned, grounding. It is a thin
wrapper over the canonical toolkit auditor (single source of truth, no drift) and
auto-detects the slug from the repo directory.

```bash
bash smoke/verify-profile.sh    # exit 0 = PASS · 1 = drift · 2 = toolkit not found
```

Needs the toolkit on disk (`~/hermes-toolkit`, or `HERMES_TOOLKIT=/path`). On drift
it prints the repair commands (re-pin / re-copy / de-bloat).
