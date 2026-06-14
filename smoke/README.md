# smoke/ — boot + login gate

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

## Definition of Done

`done-check.sh` bundles the gates a full-stack slice must pass before any "done":
backend tests + frontend tests + an API must have a UI surface + boot/login smoke.

```bash
bash smoke/done-check.sh    # exit 0 = done · 1 = not done (fix the HARD failures)
```
