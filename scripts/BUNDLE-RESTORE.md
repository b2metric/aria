# ARIA Stack — Bundle & Restore (macOS → macOS)

End-to-end "freeze-dry" the running stack and rehydrate it on another Mac.

## What's in the bundle

```
aria-bundle-YYYYMMDD-HHMM/
├── repo.tar.gz          # code + Dockerfiles + .env files + configs
├── volumes/             # one tar.gz per named docker volume
│   ├── aria-oracle-data.tar.gz                  # ~2.7 GB raw
│   ├── b2metric-aria_llm_clickhouse_data.tar.gz # ~3.1 GB raw (Langfuse)
│   ├── b2metric-aria_postgres_data.tar.gz       # ~63 MB (ARIA app DB)
│   ├── b2metric-aria_keycloak_db_data.tar.gz    # ~67 MB (realm + users)
│   ├── b2metric-aria_qdrant_data.tar.gz         # Mem0 vectors
│   └── ...
├── manifest.txt         # source host, arch, image list, sizes
├── restore-stack.sh     # the receiver-side runner
└── RESTORE.md           # this file
```

Excluded by design:
- `b2metric-aria_llm_clickhouse_logs` (regenerable, ~640 MB) — pass
  `--include-clickhouse-logs` to `bundle-stack.sh` if you want it
- Orphan volumes `aria_postgres_data` / `aria_redis_data` (not in current compose)
- `.git`, `node_modules`, `.venv`, `frontend/.next`, `tmp/`, `.playwright-mcp`

## On the SOURCE Mac

```bash
cd ~/projects/b2metric-aria
bash scripts/bundle-stack.sh
# → ~/aria-bundle-YYYYMMDD-HHMM/  (stack briefly stopped + restarted)

# package for transfer
cd ~ && tar czf aria-bundle.tgz aria-bundle-YYYYMMDD-HHMM
# move it: AirDrop, rsync, scp, USB SSD — your choice
```

Notes:
- The script **stops the stack** before tarring (clean DB snapshots). Pass
  `--no-stop` only if you've already shut Oracle/Postgres/ClickHouse down
  cleanly some other way.
- Bundle size estimate: 3–4 GB compressed (most of it Oracle + ClickHouse).

## On the TARGET Mac

Prereqs: Docker Desktop running, ≥ 8 GB RAM allocated (Oracle alone wants 4 GB).

```bash
# 1. drop the tarball anywhere and unpack
tar xzf aria-bundle.tgz
cd aria-bundle-YYYYMMDD-HHMM

# 2. restore (uses ~/projects/b2metric-aria by default; override with TARGET_REPO=...)
bash restore-stack.sh

# 3. that's it. The script:
#    - extracts the repo
#    - recreates each docker volume from its tar.gz
#    - docker compose pull + up -d --build
#    - smoke-checks aria.localhost / api / auth
```

## Cross-arch gotcha (Intel ⇄ Apple Silicon)

`manifest.txt` records `source-arch`. If source and target differ:

| Concern | What happens | Fix |
|---|---|---|
| `aria-backend` / `aria-frontend` images | Rebuilt from Dockerfile on target — fine | nothing to do |
| Public multi-arch images (postgres, redis, keycloak, traefik, …) | `docker compose pull` grabs the right arch — fine | nothing to do |
| **Oracle data files** (`aria-oracle-data`) | Oracle datafiles are arch-portable across `gvenzl/oracle-free:23-slim` arm64 ↔ amd64 builds in practice, but block-format edge cases exist. | If the container loops on startup: drop the volume, restart, and re-seed (`backend/oracle/seed.sql` + schema-discovery rerun). |
| ClickHouse | Multi-arch, format-portable | none |

## Verification on the target

```bash
docker ps --filter name=aria
curl -s http://aria.localhost                                                | head -c 80
curl -s http://api.aria.localhost/health
curl -s http://auth.aria.localhost/auth/realms/aria/.well-known/openid-configuration | head -c 80
```

All three should return data / `HTTP 200`. Login via Keycloak as the same user you had on the source — credentials are inside the realm dump.

## What you do **not** need to ship

- LiteLLM / LLM API keys you might rotate per-machine: live in `.env` /
  `backend/.env`, included in `repo.tar.gz`. Re-issue if the receiving Mac is
  someone else's.
- The sibling `hermes-llm-infra` stack on the source — ARIA doesn't depend on
  it; the bundled `aria-litellm` container is self-contained.

## Tear-down on the source (after you've confirmed the target works)

```bash
cd ~/projects/b2metric-aria
docker compose -f docker-compose.dev.yml down -v   # -v ALSO deletes volumes
```
