# Keycloak — ARIA Auth / SSO

Keycloak 26 authentication server for ARIA platform.

## Architecture

```
                  ┌─────────────────┐
                  │   Keycloak 26   │
                  │   :8080         │
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                 ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ aria-backend │ │  aria-web    │ │  aria-cli    │
   │ confidential │ │  public      │ │ confidential │
   │ svc account  │ │  OIDC + PKCE │ │  client cred │
   └──────────────┘ └──────────────┘ └──────────────┘
```

## Realm Config (`aria-realm.json`)

See `aria-realm.json` for the complete realm definition.

### Clients

| Client | Type | Auth Flow | Use Case |
|--------|------|-----------|----------|
| `aria-backend` | confidential | Client credentials + service account | Backend API auth, machine-to-machine |
| `aria-web` | public | Authorization code + PKCE | Next.js frontend user login |
| `aria-cli` | confidential | Client credentials | CLI tools, API keys |

### JWT Claims (via `aria-claims` client scope)

| Claim | Source | Type | Description |
|-------|--------|------|-------------|
| `sub` | built-in | UUID | User unique ID |
| `user_id` | user attribute | String | External user ID (from app DB) |
| `workspace_id` | user attribute | String | Current workspace context |
| `team_id` | user attribute | String | User's team |
| `role` | realm roles | String[] | Assigned realm roles |
| `email` | built-in | String | User email |
| `preferred_username` | built-in | String | Username |

### Realm Roles

| Role | Description |
|------|-------------|
| `admin` | Platform administrator |
| `workspace_owner` | Full workspace access |
| `workspace_admin` | Workspace administration |
| `workspace_editor` | Create, edit, delete resources |
| `workspace_viewer` | Read-only access |

## Quick Start

```bash
# 1. Start Keycloak with realm auto-import
docker compose -f docker-compose.dev.yml up -d keycloak keycloak-db

# 2. Wait for health check (30-60s)
docker compose -f docker-compose.dev.yml ps keycloak

# 3. Run bootstrap to set initial passwords
./bootstrap.sh

# 4. Open admin console
open http://localhost:8080/admin/aria/console/
```

## Bootstrap Script

`./bootstrap.sh` uses the Keycloak Admin REST API to:
1. Authenticate as bootstrap admin (master realm)
2. Set password for `admin@b2metric.com` user in the `aria` realm
3. Display client secrets for `aria-backend` and `aria-cli`

## Keycloak Endpoints

| Endpoint | URL |
|----------|-----|
| Admin Console | http://localhost:8080/admin/aria/console/ |
| OIDC Discovery | http://localhost:8080/realms/aria/.well-known/openid-configuration |
| Token Endpoint | http://localhost:8080/realms/aria/protocol/openid-connect/token |
| User Info | http://localhost:8080/realms/aria/protocol/openid-connect/userinfo |
| JWKS (certs) | http://localhost:8080/realms/aria/protocol/openid-connect/certs |

## Testing

```bash
# Get OIDC discovery
curl -s http://localhost:8080/realms/aria/.well-known/openid-configuration | jq

# Client credentials grant (aria-backend)
curl -s -X POST http://localhost:8080/realms/aria/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=aria-backend" \
  -d "client_secret=aria-backend-secret-change-in-production" | jq

# Decode JWT
curl -s -X POST http://localhost:8080/realms/aria/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=aria-backend" \
  -d "client_secret=aria-backend-secret-change-in-production" \
  | jq -r '.access_token' \
  | cut -d. -f2 | base64 -d | jq
```
