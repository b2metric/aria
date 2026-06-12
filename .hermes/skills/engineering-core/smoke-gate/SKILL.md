---
name: smoke-gate
description: Use before declaring ANY full-stack change complete - proves the stack boots and a real user can log in end-to-end, catching "system down" and "up-but-can't-login" classes before a done-claim
---

# Smoke Gate (boot + login)

**REQUIRED BACKGROUND:** engineering-core:verification-before-completion. This skill is the full-stack instance of it.

## The Iron Law

**NO COMPLETION CLAIM WITHOUT A GREEN BOOT + LOGIN SMOKE.**

If you have not, in this session, watched the stack come up AND watched a real login round-trip succeed, the work is NOT done — regardless of unit tests passing, builds succeeding, or how confident you feel.

This gate exists because two entire failure classes shipped undetected: **"system shut down" (app never booted)** and **"system up but login broken"** (a Keycloak JWKS `/auth` path mismatch returned 500s on every authentication). Nothing ever exercised boot + login, so nothing caught them.

## When this fires

Any change to: backend services, auth/IdP config, docker-compose, env/secrets, reverse-proxy (Traefik) routing, database/migrations, or anything that could affect whether the app starts or a user can sign in.

## The Gate (run in order; STOP on the first failure)

1. **Bring the stack up** — `docker compose up -d` (or the project's start command). Capture exit codes.
2. **Health-poll every service** — poll each service's health endpoint until `200` or timeout (use engineering-core:condition-based-waiting — poll the condition, never `sleep`). A service that never goes healthy is a FAILED gate. List which service failed.
3. **Resolve the IdP discovery + JWKS** — fetch the OIDC discovery doc and the JWKS endpoint and assert both return `200` with the EXPECTED path. For Keycloak ≥ 26 with `KC_HTTP_RELATIVE_PATH=/auth`, JWKS lives at `…/auth/realms/<realm>/protocol/openid-connect/certs`. A `404`/wrong-path here is the classic login-breaker — assert the exact URL the backend will call.
4. **Drive a REAL login** — perform an actual end-to-end login (Playwright against the running frontend, or a direct OIDC password-grant) using a seeded test user. Assert you receive a valid token.
5. **Verify the token + one authenticated request** — call one protected backend endpoint with the token and assert `200`. This proves the issuer/audience/JWKS all line up, not just that a login page rendered.
6. **Emit the smoke report** — a short artifact: each service's health, the JWKS URL checked, login result, the authenticated call result. This artifact is the evidence `verification-before-completion` requires.

## Red Flags — STOP, the gate is not green

| Thought | Reality |
|---------|---------|
| "Unit tests pass, so it works" | Unit tests never started the stack or logged in. Run the gate. |
| "The login page renders" | A rendered page ≠ a working login. Token must verify against JWKS. |
| "I only changed the backend, auth is fine" | Issuer/JWKS/audience break silently across services. Re-run login. |
| "Keycloak shows unhealthy but it's probably fine" | Prove it: fetch the exact JWKS URL the backend uses and get a token. |
| "I'll add a smoke test later" | Later = never. No done without the green smoke now. |

## Failure handling

A failed gate is NOT "done with a known issue." Re-open the task and route to engineering-core:systematic-debugging to find the root cause (which service, which boundary, which config) — do not patch symptoms or bump timeouts.

## Artifact

`smoke/` directory in every full-stack project: a health-check script + a login E2E (`login.spec.ts`) + an explicit JWKS/issuer assertion. CI runs it; completion is blocked until it is green.
