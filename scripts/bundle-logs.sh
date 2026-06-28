#!/usr/bin/env bash
# bundle-logs.sh — capture every relevant aria-* container's stdout + Langfuse
# trace export into a single tar.gz for off-machine analysis.
#
# Run on the host where the stack is up (no repo dependency — only docker).
# Default window: last 1 hour. Override with --since.
#
# Usage:
#   bash bundle-logs.sh                       # last 1h, primary containers
#   bash bundle-logs.sh --since 30m           # last 30 minutes
#   bash bundle-logs.sh --since 6h --all      # 6h, every aria-* container
#   bash bundle-logs.sh --no-langfuse         # skip ClickHouse trace export
#   bash bundle-logs.sh --no-redact           # keep secrets visible (USE WITH CARE)
#   bash bundle-logs.sh --out /tmp/aria.tgz   # custom output path
#
# What it captures:
#   - docker logs --timestamps --since=$WIN   for each container
#   - Langfuse traces + observations from aria-clickhouse (last 1000 / 5000)
#   - container status snapshot + manifest
#   - SHA256 of each file (so tampering after bundling is visible)
#
# Redaction (default ON) strips:
#   - Authorization: Bearer ...
#   - api_key=... / apikey=... / token=...
#   - password=... / PASSWORD=...
#   - JWT-shaped strings (eyJ...) longer than 40 chars
#   - Keycloak realm passwords, Oracle passwords, MinIO secrets
# Pass --no-redact only when you trust the destination of the bundle.

set -euo pipefail

# ── defaults ──────────────────────────────────────────────────────────────────
SINCE="1h"
INCLUDE_ALL=0
SKIP_LANGFUSE=0
REDACT=1
STAMP="$(date +%Y%m%d-%H%M)"
OUT_PATH="$HOME/aria-logs-$STAMP.tar.gz"

PRIMARY=(
  aria-backend
  aria-frontend
  aria-litellm
  aria-langfuse-web
  aria-langfuse-worker
  aria-keycloak
  aria-traefik
  aria-clickhouse
  aria-postgres
  aria-oracle
)
ALL=(
  aria-backend aria-frontend aria-litellm
  aria-langfuse-web aria-langfuse-worker
  aria-keycloak aria-keycloak-db
  aria-traefik
  aria-clickhouse aria-postgres aria-redis
  aria-llm-postgres aria-llm-redis aria-llm-minio
  aria-minio aria-qdrant
  aria-prefect-server aria-prefect-db
  aria-oracle
)

# ── arg parse ─────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)        SINCE="$2"; shift 2 ;;
    --all)          INCLUDE_ALL=1; shift ;;
    --no-langfuse)  SKIP_LANGFUSE=1; shift ;;
    --no-redact)    REDACT=0; shift ;;
    --out)          OUT_PATH="$2"; shift 2 ;;
    -h|--help)      sed -n '2,28p' "$0"; exit 0 ;;
    *)              echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

CONTAINERS=("${PRIMARY[@]}")
[[ "$INCLUDE_ALL" == 1 ]] && CONTAINERS=("${ALL[@]}")

log() { printf '\033[36m[logs]\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m[logs]\033[0m %s\n' "$*"; }
warn(){ printf '\033[33m[logs]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[logs]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "docker not found in PATH"
docker info >/dev/null 2>&1 || die "docker daemon not reachable"

WORK_DIR="$(mktemp -d -t aria-logs-XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT
BUNDLE_DIR="$WORK_DIR/aria-logs-$STAMP"
mkdir -p "$BUNDLE_DIR/containers" "$BUNDLE_DIR/langfuse"

log "window: --since=$SINCE   containers: ${#CONTAINERS[@]}   redact: $REDACT"
log "staging in: $BUNDLE_DIR"

# ── redactor (sed) ────────────────────────────────────────────────────────────
# Multi-pattern, applied IN PLACE on each captured file before bundling.
redact_file() {
  local f="$1"
  [[ "$REDACT" == 1 ]] || return 0
  # macOS sed needs -i ''
  sed -E -i.bak \
    -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[A-Za-z0-9._~+/=-]{16,}/\1***REDACTED***/Ig' \
    -e 's/((api[_-]?key|apikey|token|secret|client[_-]?secret)[[:space:]]*[:=][[:space:]]*"?)[^"[:space:],}]{8,}/\1***REDACTED***/Ig' \
    -e 's/((password|passwd|pwd)[[:space:]]*[:=][[:space:]]*"?)[^"[:space:],}]+/\1***REDACTED***/Ig' \
    -e 's/(eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})/***REDACTED-JWT***/g' \
    -e 's/(sk-[A-Za-z0-9]{20,})/***REDACTED-OPENAI***/g' \
    -e 's/(pat-[A-Za-z0-9._-]{20,})/***REDACTED-LITELLM***/g' \
    -e 's/(lf_pk_[A-Za-z0-9]{16,})/***REDACTED-LANGFUSE-PK***/g' \
    -e 's/(lf_sk_[A-Za-z0-9]{16,})/***REDACTED-LANGFUSE-SK***/g' \
    "$f"
  rm -f "$f.bak"
}

# ── container logs ────────────────────────────────────────────────────────────
log "capturing container logs"
for c in "${CONTAINERS[@]}"; do
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$c"; then
    warn "  SKIP $c (not present)"
    continue
  fi
  out="$BUNDLE_DIR/containers/$c.log"
  if docker logs --timestamps --since="$SINCE" "$c" >"$out" 2>&1; then
    sz=$(wc -l <"$out" | tr -d ' ')
    log "  $c → $sz lines"
    redact_file "$out"
  else
    warn "  $c → docker logs failed (kept partial output)"
  fi
done

# container status snapshot
docker ps -a --filter name=aria --format \
  'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' \
  >"$BUNDLE_DIR/containers/_status.txt" 2>/dev/null || true

# ── Langfuse trace export from ClickHouse (best-effort) ───────────────────────
if [[ "$SKIP_LANGFUSE" == 0 ]] && docker ps --format '{{.Names}}' | grep -qx aria-clickhouse; then
  log "exporting Langfuse traces from ClickHouse"
  # Recent traces (last 1000) and observations (last 5000). JSONEachRow is one
  # JSON object per line — easy to grep / parse downstream.
  for tbl_q in \
      "traces|SELECT * FROM traces ORDER BY timestamp DESC LIMIT 1000 FORMAT JSONEachRow" \
      "observations|SELECT * FROM observations ORDER BY start_time DESC LIMIT 5000 FORMAT JSONEachRow" \
      "scores|SELECT * FROM scores ORDER BY timestamp DESC LIMIT 2000 FORMAT JSONEachRow"
  do
    name="${tbl_q%%|*}"
    sql="${tbl_q#*|}"
    out="$BUNDLE_DIR/langfuse/$name.jsonl"
    if docker exec aria-clickhouse clickhouse-client --query "$sql" >"$out" 2>/dev/null; then
      sz=$(wc -l <"$out" | tr -d ' ')
      log "  $name → $sz rows"
      redact_file "$out"
    else
      warn "  $name → ClickHouse query failed (table may be missing or empty)"
      rm -f "$out"
    fi
  done
else
  log "skipping Langfuse export (--no-langfuse or aria-clickhouse not running)"
fi

# ── manifest ──────────────────────────────────────────────────────────────────
log "writing manifest"
{
  echo "# ARIA log bundle manifest"
  echo "created:       $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "source-host:   $(hostname)"
  echo "source-arch:   $(uname -m)"
  echo "source-os:     $(sw_vers -productName 2>/dev/null || uname -s) $(sw_vers -productVersion 2>/dev/null || uname -r)"
  echo "docker:        $(docker --version)"
  echo "window:        --since=$SINCE"
  echo "redacted:      $REDACT"
  echo
  echo "## container statuses (at capture time)"
  cat "$BUNDLE_DIR/containers/_status.txt" 2>/dev/null || true
  echo
  echo "## captured files (size + sha256)"
  ( cd "$BUNDLE_DIR" && find . -type f ! -name 'manifest.txt' -print0 \
    | xargs -0 shasum -a 256 | awk '{print $2, $1}' \
    | while read -r p h; do
        s=$(wc -c <"$BUNDLE_DIR/${p#./}" | tr -d ' ')
        printf '  %-50s %10s bytes  sha256=%s\n' "${p#./}" "$s" "$h"
      done )
} >"$BUNDLE_DIR/manifest.txt"

# ── tar it up ─────────────────────────────────────────────────────────────────
log "creating tarball"
tar -czf "$OUT_PATH" -C "$WORK_DIR" "aria-logs-$STAMP"
BUNDLE_SIZE=$(du -sh "$OUT_PATH" | cut -f1)

ok "done."
log "output:  $OUT_PATH ($BUNDLE_SIZE)"
log "verify:  tar -tzf $OUT_PATH | head"
log "send to: AirDrop / scp / drag-into-chat"
[[ "$REDACT" == 0 ]] && warn "secrets NOT redacted — handle the bundle with care."
