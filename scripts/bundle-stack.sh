#!/usr/bin/env bash
# bundle-stack.sh — freeze-dry the full ARIA stack (code + configs + DB volumes)
# into a single transferable directory. Run on the SOURCE Mac.
#
# Output: $OUT_DIR/aria-bundle-YYYYMMDD-HHMM/
#   repo.tar.gz                  -- code, .env files, configs, Dockerfiles
#   volumes/<name>.tar.gz        -- each named docker volume
#   manifest.txt                 -- versions, image list, source-arch
#   restore-stack.sh             -- copy of the restore script
#   RESTORE.md                   -- step-by-step receiver instructions
#
# Pass --include-clickhouse-logs to also tar the 600M+ logs volume (regenerable).
# Pass --no-stop to skip stopping containers (risk: half-flushed DB snapshots).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$HOME}"
STAMP="$(date +%Y%m%d-%H%M)"
BUNDLE_DIR="$OUT_DIR/aria-bundle-$STAMP"
INCLUDE_CLICKHOUSE_LOGS=0
STOP_STACK=1

for arg in "$@"; do
  case "$arg" in
    --include-clickhouse-logs) INCLUDE_CLICKHOUSE_LOGS=1 ;;
    --no-stop) STOP_STACK=0 ;;
    -h|--help)
      sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

VOLUMES=(
  aria-oracle-data
  b2metric-aria_postgres_data
  b2metric-aria_keycloak_db_data
  b2metric-aria_qdrant_data
  b2metric-aria_minio_data
  b2metric-aria_llm_postgres_data
  b2metric-aria_llm_clickhouse_data
  b2metric-aria_llm_minio_data
  b2metric-aria_llm_redis_data
  b2metric-aria_redis_data
  b2metric-aria_prefect_db_data
)
if [[ "$INCLUDE_CLICKHOUSE_LOGS" == 1 ]]; then
  VOLUMES+=( b2metric-aria_llm_clickhouse_logs )
fi

log() { printf '\033[36m[bundle]\033[0m %s\n' "$*"; }

mkdir -p "$BUNDLE_DIR/volumes"
log "writing to $BUNDLE_DIR"

if [[ "$STOP_STACK" == 1 ]]; then
  log "stopping stack for consistent snapshot (containers only — volumes preserved)"
  (cd "$REPO_DIR" && docker compose -f docker-compose.dev.yml stop)
fi

log "tarring named volumes"
for v in "${VOLUMES[@]}"; do
  if ! docker volume inspect "$v" >/dev/null 2>&1; then
    log "  SKIP $v (does not exist)"
    continue
  fi
  log "  -> $v"
  docker run --rm \
    -v "$v":/data:ro \
    -v "$BUNDLE_DIR/volumes":/out \
    alpine sh -c "cd /data && tar czf /out/$v.tar.gz ."
done

log "tarring repo (code, .env files, configs)"
tar --exclude='./.git' \
    --exclude='./node_modules' \
    --exclude='./**/node_modules' \
    --exclude='./.venv' \
    --exclude='./**/.venv' \
    --exclude='./__pycache__' \
    --exclude='./**/__pycache__' \
    --exclude='./frontend/.next' \
    --exclude='./frontend/out' \
    --exclude='./tmp' \
    --exclude='./.playwright-mcp' \
    --exclude='./.pytest_cache' \
    --exclude='./**/.pytest_cache' \
    --exclude='./dist' \
    --exclude='./**/*.pyc' \
    --exclude='./**/*.log' \
    -czf "$BUNDLE_DIR/repo.tar.gz" \
    -C "$REPO_DIR" .

log "writing manifest"
{
  echo "# ARIA bundle manifest"
  echo "created:       $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "source-host:   $(hostname)"
  echo "source-arch:   $(uname -m)"
  echo "source-os:     $(sw_vers -productName) $(sw_vers -productVersion)"
  echo "docker:        $(docker --version)"
  echo "compose:       $(docker compose version --short 2>/dev/null || docker compose version)"
  echo
  echo "## images in use (re-pulled / re-built on target)"
  docker ps -a --filter name=aria --format '{{.Names}}  {{.Image}}' | sort
  echo
  echo "## bundled volumes"
  ls -lh "$BUNDLE_DIR/volumes" | awk 'NR>1 {print $9, $5}'
  echo
  echo "## repo archive"
  ls -lh "$BUNDLE_DIR/repo.tar.gz" | awk '{print $9, $5}'
} > "$BUNDLE_DIR/manifest.txt"

cp "$REPO_DIR/scripts/restore-stack.sh" "$BUNDLE_DIR/restore-stack.sh"
cp "$REPO_DIR/scripts/BUNDLE-RESTORE.md" "$BUNDLE_DIR/RESTORE.md"
chmod +x "$BUNDLE_DIR/restore-stack.sh"

if [[ "$STOP_STACK" == 1 ]]; then
  log "restarting stack"
  (cd "$REPO_DIR" && docker compose -f docker-compose.dev.yml start) || true
fi

log "done."
log "size: $(du -sh "$BUNDLE_DIR" | cut -f1)"
log "next: tar czf aria-bundle-$STAMP.tar.gz -C $OUT_DIR aria-bundle-$STAMP   # for transfer"
