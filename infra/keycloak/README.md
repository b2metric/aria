# ARIA Keycloak Setup

## Realm: `aria`

ARIA platform authentication uses **Keycloak 26** with a pre-configured realm.

### Quick Start

```bash
# 1. Start Keycloak (imports realm automatically)
docker compose -f docker-compose.dev.yml up -d keycloak

# 2. Wait for Keycloak to be healthy, then bootstrap passwords
./infra/keycloak/bootstrap.sh
```

### Realm Configuration (`aria-realm.json`)

| Component | Details |
|---|---|
| **Realm** | `aria` |
| **Clients** | `aria-backend` (confidential, service account), `aria-web` (public, PKCE), `aria-cli` (machine-to-machine) |
| **Roles** | `admin`, `team_lead`, `analyst`, `viewer` |
| **Custom Claims** | `workspace_id`, `user_id`, `team_id`, `role` — mapped from user attributes via `aria-claims` client scope |
| **Token Signature** | RS256 (asymmetric) |
| **Seed User** | `admin` / `admin` (temporary — reset by bootstrap.sh) |

### Custom JWT Claims

The `aria-claims` client scope injects the following claims into every access token:

| Claim | Source | Example |
|---|---|---|
| `workspace_id` | User attribute `workspace_id` | `"ws-abc123"` |
| `user_id` | User attribute `user_id` | `"usr-001"` |
| `team_id` | User attribute `team_id` | `"team-xyz"` |
| `role` | User attribute `aria_role` | `"analyst"` |

### Role Matrix

| Role | Can query | Can view SQL | Can manage team | Can admin |
|---|---|---|---|---|
| `admin` | ✅ | ✅ | ✅ | ✅ |
| `team_lead` | ✅ | ❌ | ✅ | ❌ |
| `analyst` | ✅ | ✅ | ❌ | ❌ |
| `viewer` | ✅ (read-only) | ❌ | ❌ | ❌ |

### Bootstrap Script

`bootstrap.sh` performs the following post-startup tasks:
1. Waits for Keycloak admin endpoint
2. Sets the `admin` user password to non-temporary
3. Generates a client secret for `aria-backend`
4. Prints the secret for `.env` configuration

### Environment Variables

```env
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=aria
KEYCLOAK_CLIENT_ID=aria-backend
KEYCLOAK_CLIENT_SECRET=<from bootstrap.sh output>
```
