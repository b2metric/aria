# Infrastructure

Docker, Kubernetes manifests, CI/CD pipelines, and deployment configs for ARIA.

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `keycloak/` | Keycloak 26 realm config, OIDC clients, JWT claims, bootstrap script |
| (future) | Kubernetes, Terraform, CI/CD |

## Quick Start

```bash
# Start all infra
docker compose -f docker-compose.dev.yml up -d

# Bootstrap Keycloak (after all services healthy)
./infra/keycloak/bootstrap.sh
```

See `docker-compose.dev.yml` for service definitions and `infra/keycloak/README.md` for Keycloak-specific docs.
