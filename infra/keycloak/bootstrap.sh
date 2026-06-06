#!/bin/bash
# ─── ARIA Keycloak Bootstrap ──────────────────────────────────────────
# Sets initial passwords for imported realm users via Keycloak Admin REST API.
# Uses KC_BOOTSTRAP_ADMIN credentials (master realm) to manage the aria realm.
#
# Usage: ./bootstrap-keycloak.sh [KEYCLOAK_URL]
#   Default KEYCLOAK_URL: http://localhost:8080

set -euo pipefail

KC_URL="${1:-http://localhost:8080}"
KC_ADMIN="${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}"
KC_ADMIN_PW="${KC_BOOTSTRAP_ADMIN_PASSWORD:-admin}"
REALM="aria"

# ── Check if aria realm exists ────────────────────────────────────────
echo ">>> Checking if '$REALM' realm is available..."
REALM_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$KC_URL/realms/$REALM" 2>/dev/null || echo "000")

if [ "$REALM_CHECK" != "200" ]; then
  echo "ERROR: Realm '$REALM' not found at $KC_URL. Is Keycloak running with --import-realm?"
  echo "  Status code: $REALM_CHECK"
  exit 1
fi

echo ">>> Realm '$REALM' found. Getting admin token..."

# ── Get master realm admin token ───────────────────────────────────────
ADMIN_TOKEN=$(curl -s -X POST "$KC_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=$KC_ADMIN" \
  -d "password=$KC_ADMIN_PW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$ADMIN_TOKEN" ]; then
  echo "ERROR: Could not authenticate as bootstrap admin."
  echo "  Check KC_BOOTSTRAP_ADMIN_USERNAME and KC_BOOTSTRAP_ADMIN_PASSWORD."
  exit 1
fi

echo ">>> Admin token obtained."

# ── Helper: set user password ──────────────────────────────────────────
set_user_password() {
  local USERNAME="$1"
  local PASSWORD="$2"
  local USER_ID

  USER_ID=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KC_URL/admin/realms/$REALM/users?username=$USERNAME" \
    | python3 -c "import sys,json; users=json.load(sys.stdin); print(users[0]['id'] if users else '')" 2>/dev/null)

  if [ -z "$USER_ID" ]; then
    echo "  WARNING: User '$USERNAME' not found in realm '$REALM'. Skipping."
    return
  fi

  curl -s -X PUT "$KC_URL/admin/realms/$REALM/users/$USER_ID/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"password\",\"value\":\"$PASSWORD\",\"temporary\":false}" \
    > /dev/null

  echo "  User '$USERNAME': password set (id=$USER_ID)"
}

# ── Get client secret ──────────────────────────────────────────────────
get_client_secret() {
  local CLIENT_ID="$1"
  local CLIENT_UUID

  CLIENT_UUID=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KC_URL/admin/realms/$REALM/clients?clientId=$CLIENT_ID" \
    | python3 -c "import sys,json; clients=json.load(sys.stdin); print(clients[0]['id'] if clients else '')" 2>/dev/null)

  if [ -z "$CLIENT_UUID" ]; then
    echo "  WARNING: Client '$CLIENT_ID' not found."
    return
  fi

  SECRET=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KC_URL/admin/realms/$REALM/clients/$CLIENT_UUID/client-secret" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('value',''))" 2>/dev/null)

  echo "  Client '$CLIENT_ID': secret=$SECRET"
}

# ── Set passwords ──────────────────────────────────────────────────────
echo ""
echo ">>> Setting user passwords..."
set_user_password "admin" "aria-admin-$(date +%Y)"

# ── Show client secrets ────────────────────────────────────────────────
echo ""
echo ">>> Client secrets:"
get_client_secret "aria-backend"
get_client_secret "aria-cli"

echo ""
echo ">>> Bootstrap complete."
echo ""
echo "  Realm:        $REALM"
echo "  Admin user:   admin@b2metric.com"
echo "  Keycloak URL: $KC_URL"
echo "  Admin UI:     $KC_URL/admin/$REALM/console/"
echo ""
echo "  Clients:"
echo "    aria-backend  (confidential) → service account + client credentials"
echo "    aria-web      (public)       → standard OIDC flow + PKCE"
echo "    aria-cli      (confidential) → client credentials for API keys"
