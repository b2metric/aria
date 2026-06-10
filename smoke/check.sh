#!/bin/bash
# ── smoke/check.sh — boot + login gate (engineering-core:smoke-gate) ──────────
# Proves: backend boots (/health 200), Keycloak JWKS resolves at the EXACT /auth
# path the backend uses, and (if creds given) a real OIDC login round-trips and an
# authenticated request succeeds. Exit != 0 on any failure -> blocks completion.
set -uo pipefail

BACKEND="${SMOKE_BACKEND_URL:-http://localhost:8000}"
KC="${SMOKE_KEYCLOAK_URL:-http://localhost:8080/auth}"
REALM="${SMOKE_REALM:-aria}"
JWKS="$KC/realms/$REALM/protocol/openid-connect/certs"
TOKEN_URL="$KC/realms/$REALM/protocol/openid-connect/token"
fail=0
pass() { printf '  \033[0;32mPASS\033[0m %s\n' "$1"; }
bad()  { printf '  \033[0;31mFAIL\033[0m %s\n' "$1"; fail=1; }

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$1" 2>/dev/null; }

echo "== smoke gate =="
# 1) backend health (poll up to ~30s)
ok=0
for i in $(seq 1 15); do
  [ "$(code "$BACKEND/health")" = "200" ] && { ok=1; break; }
  sleep 2
done
[ "$ok" = "1" ] && pass "backend /health 200 ($BACKEND)" || bad "backend /health not 200 ($BACKEND) — system down"

# 2) Keycloak JWKS at the EXACT /auth path (the login-breaker trap)
JC="$(code "$JWKS")"
[ "$JC" = "200" ] && pass "JWKS 200 ($JWKS)" || bad "JWKS $JC ($JWKS) — login will 500 (check /auth path + realm)"

# 3) optional real login round-trip
if [ -n "${SMOKE_TEST_USER:-}" ] && [ -n "${SMOKE_TEST_PASS:-}" ] && [ -n "${SMOKE_CLIENT_ID:-}" ]; then
  RESP="$(curl -s --max-time 10 -X POST "$TOKEN_URL" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "grant_type=password" -d "client_id=${SMOKE_CLIENT_ID}" \
    ${SMOKE_CLIENT_SECRET:+-d "client_secret=${SMOKE_CLIENT_SECRET}"} \
    -d "username=${SMOKE_TEST_USER}" -d "password=${SMOKE_TEST_PASS}" 2>/dev/null)"
  TOKEN="$(printf '%s' "$RESP" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')"
  if [ -n "$TOKEN" ]; then
    pass "OIDC login returned a token"
    MC="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 -H "Authorization: Bearer $TOKEN" "$BACKEND/me" 2>/dev/null)"
    [ "$MC" = "200" ] && pass "authenticated GET /me 200 (token verifies vs JWKS)" || bad "GET /me $MC — token did not verify (issuer/JWKS mismatch)"
  else
    bad "OIDC login did not return a token (resp: ${RESP:0:160})"
  fi
else
  echo "  (login round-trip skipped — set SMOKE_TEST_USER/PASS/CLIENT_ID to enable)"
fi

echo "== $([ $fail -eq 0 ] && echo 'SMOKE GREEN' || echo 'SMOKE FAILED') =="
exit $fail
