#!/usr/bin/env bash
# restore-stack.sh — restore an ARIA bundle on a fresh macOS.
# Run this from inside the unpacked aria-bundle-* directory.
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_REPO="${TARGET_REPO:-$HOME/projects/b2metric-aria}"

log() { printf '\033[32m[restore]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[restore]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -d "$BUNDLE_DIR/volumes" ]] || die "no volumes/ in $BUNDLE_DIR — wrong cwd?"
[[ -f "$BUNDLE_DIR/repo.tar.gz" ]] || die "no repo.tar.gz in $BUNDLE_DIR"
docker info >/dev/null 2>&1 || die "Docker Desktop is not running"

log "source arch / target arch:"
grep -E 'source-arch' "$BUNDLE_DIR/manifest.txt" || true
echo "target-arch:   $(uname -m)"
echo

# 1. extract the repo
if [[ -d "$TARGET_REPO" && -n "$(ls -A "$TARGET_REPO" 2>/dev/null)" ]]; then
  read -p "$TARGET_REPO already exists and is non-empty. Overwrite? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "aborted"
fi
mkdir -p "$TARGET_REPO"
log "extracting repo -> $TARGET_REPO"
tar xzf "$BUNDLE_DIR/repo.tar.gz" -C "$TARGET_REPO"

# 2. create + restore each named volume
for tgz in "$BUNDLE_DIR"/volumes/*.tar.gz; do
  vol="$(basename "$tgz" .tar.gz)"
  log "restoring volume: $vol"
  if docker volume inspect "$vol" >/dev/null 2>&1; then
    read -p "  volume $vol exists. Remove and replace? [y/N] " ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
      docker volume rm "$vol" >/dev/null
    else
      log "  SKIP $vol"
      continue
    fi
  fi
  docker volume create "$vol" >/dev/null
  docker run --rm \
    -v "$vol":/data \
    -v "$BUNDLE_DIR/volumes":/in:ro \
    alpine sh -c "cd /data && tar xzf /in/$vol.tar.gz"
done

# 3. Remove any stale aria-net network that lacks the compose label.
#    The main compose file (docker-compose.dev.yml) declares `aria-net` non-external
#    and creates it itself with proper labels. The included infra/llm/*.yml then
#    refers to the SAME network as external and resolves to compose's creation.
#    But if a label-less `aria-net` already exists (e.g. manually created), compose
#    errors with "network was found but has incorrect label".
if docker network inspect aria-net >/dev/null 2>&1; then
  if ! docker network inspect aria-net --format '{{.Labels}}' | grep -q 'com.docker.compose.network:aria-net'; then
    log "removing stale label-less aria-net network so compose can recreate it"
    docker network rm aria-net >/dev/null || log "  (could not remove — containers may be using it)"
  fi
fi

# 4. pull public images + build local ones, then start
log "pulling + building images (this is slow the first time)"
cd "$TARGET_REPO"
docker compose -f docker-compose.dev.yml pull --ignore-buildable || true
docker compose -f docker-compose.dev.yml up -d --build

log "waiting 20s for services to settle..."
sleep 20

log "smoke check"
for u in http://aria.localhost http://api.aria.localhost/health http://auth.aria.localhost/auth/realms/aria/.well-known/openid-configuration; do
  printf '  %-70s ' "$u"
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' --max-time 8 "$u" || echo 'curl failed'
done

cat <<EOF

[restore] done.

If any *.aria.localhost URL did not return 200, check:
  1. /etc/hosts has *.localhost wildcard handling (built into macOS) — usually fine
  2. Docker Desktop has enough RAM (Oracle needs >= 4 GB)
  3. docker compose -f docker-compose.dev.yml logs -f <service>

If Oracle (aria-oracle) fails to start on a different CPU architecture than the
source, the volume's datafiles may be arch-incompatible. Fallback: drop the
volume and recreate the schema from backend/oracle/seed.sql (or re-run the
schema-discovery flow).
EOF
