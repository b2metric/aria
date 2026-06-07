#!/usr/bin/env bash
set -euo pipefail

# ─── ARIA Keycloak Bootstrap ─────────────────────────────────────────────
# Run after `docker compose -f docker-compose.dev.yml up -d keycloak`
# Sets non-temporary passwords for pre-seeded users and creates a test
# service-account client secret for aria-backend.

KC_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KC_ADMIN="${KC_ADMIN_USER:-admin}"
KC_ADMIN_PASS="${KC_ADMIN_PASSWORD:-admin}"
REALM="aria"

echo "==> Waiting for Keycloak admin endpoint..."
until curl -sf "${KC_URL}/admin/realms/${REALM}" > /dev/null 2>&1; do
    sleep 3
done
echo "    Keycloak is ready."

# Get admin token
TOKEN=$(curl -sf -X POST "${KC_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "username=${KC_ADMIN}" \
    -d "password=${KC_ADMIN_PASS}" \
    -d "grant_type=password" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

AUTH="Authorization: Bearer ${TOKEN}"

# ── Set admin user password (non-temporary) ──────────────────────────────
echo "==> Resetting admin user password..."
ADMIN_USER_ID=$(curl -sf "${KC_URL}/admin/realms/${REALM}/users?username=admin" \
    -H "${AUTH}" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

curl -sf -X PUT "${KC_URL}/admin/realms/${REALM}/users/${ADMIN_USER_ID}/reset-password" \
    -H "${AUTH}" \
    -H "Content-Type: application/json" \
    -d '{"type":"password","value":"admin","temporary":false}' > /dev/null
echo "    admin password set (non-temporary)."

# ── Create aria-backend client secret ────────────────────────────────────
echo "==> Setting aria-backend client secret..."
CLIENT_ID=$(curl -sf "${KC_URL}/admin/realms/${REALM}/clients?clientId=aria-backend" \
    -H "${AUTH}" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

curl -sf -X POST "${KC_URL}/admin/realms/${REALM}/clients/${CLIENT_ID}/client-secret" \
    -H "${AUTH}" > /dev/null

# Read back the secret
SECRET=$(curl -sf "${KC_URL}/admin/realms/${REALM}/clients/${CLIENT_ID}/client-secret" \
    -H "${AUTH}" | python3 -c "import sys,json; print(json.load(sys.stdin)['value'])")

echo "    Client secret created."
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ARIA KEYCLOAK BOOTSTRAP COMPLETE                            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Admin URL:    ${KC_URL}/admin/${REALM}/console                "
echo "║  Admin User:   admin / admin                                ║"
echo "║  Backend Client Secret:                                      ║"
echo "║    ${SECRET}"
echo "║                                                              ║"
echo "║  Add this to your .env:                                      ║"
echo "║    KEYCLOAK_CLIENT_SECRET=${SECRET}"
echo "╚══════════════════════════════════════════════════════════════╝"
