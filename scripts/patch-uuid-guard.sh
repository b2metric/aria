#!/usr/bin/env bash
# patch-uuid-guard.sh — apply the UUID-guard fix to query.py and rbac.py.
#
# Fixes log noise + spurious 403s when the auth layer carries a non-UUID
# user_id (e.g. legacy "admin-001" claim or "unknown-user" fallback) while
# users.id is a Postgres UUID column.
#
# Idempotent: re-running is a no-op once both files contain the guard.
# Run from the repo root (~/projects/b2metric-aria by default).
#
# Usage:
#   bash scripts/patch-uuid-guard.sh
#   # then: docker compose -f docker-compose.dev.yml restart backend
#   # (uvicorn --reload also picks it up automatically)

set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
QUERY_FILE="$REPO_DIR/backend/app/api/query.py"
RBAC_FILE="$REPO_DIR/backend/app/auth/rbac.py"

log() { printf '\033[36m[patch]\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m[patch]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[patch]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f "$QUERY_FILE" ]] || die "not found: $QUERY_FILE  (run from repo root or pass repo dir as arg)"
[[ -f "$RBAC_FILE"  ]] || die "not found: $RBAC_FILE"

python3 - "$QUERY_FILE" "$RBAC_FILE" <<'PYEOF'
import sys, pathlib

QUERY_OLD = '''    from sqlalchemy import text as _text

    if not user.user_id:
        return resolve_effective_sql_visibility(user.role, sql_visibility=None)

    try:
        async with engine.connect() as conn:'''

QUERY_NEW = '''    import uuid as _uuid

    from sqlalchemy import text as _text

    if not user.user_id:
        return resolve_effective_sql_visibility(user.role, sql_visibility=None)

    # users.id is UUID. Non-UUID identifiers (legacy `admin-001` custom claim,
    # `unknown-user` auth fallback, etc.) can never match a DB row, so skip the
    # lookup and fall back to the role default instead of failing closed on a
    # noisy asyncpg ValueError every request.
    try:
        _uuid.UUID(str(user.user_id))
    except (ValueError, TypeError):
        return resolve_effective_sql_visibility(user.role, sql_visibility=None)

    try:
        async with engine.connect() as conn:'''

RBAC_OLD = '''    from sqlalchemy import text as _text

    from backend.app.db.session import get_sessionmaker
    from backend.app.query.sql_visibility import resolve_effective_sql_visibility

    if user.user_id:
        try:
            maker = get_sessionmaker()
            async with maker() as session:'''

RBAC_NEW = '''    import uuid as _uuid

    from sqlalchemy import text as _text

    from backend.app.db.session import get_sessionmaker
    from backend.app.query.sql_visibility import resolve_effective_sql_visibility

    # users.id is UUID. Non-UUID identifiers (legacy `admin-001` custom claim,
    # `unknown-user` auth fallback, etc.) cannot match a DB row — skip the lookup
    # so we don't 403 every protected endpoint for these users; fall back to the
    # role default instead.
    looks_like_uuid = False
    if user.user_id:
        try:
            _uuid.UUID(str(user.user_id))
            looks_like_uuid = True
        except (ValueError, TypeError):
            looks_like_uuid = False

    if user.user_id and looks_like_uuid:
        try:
            maker = get_sessionmaker()
            async with maker() as session:'''

def patch(path: str, old: str, new: str, sentinel: str) -> str:
    p = pathlib.Path(path)
    src = p.read_text()
    if sentinel in src:
        return f"already patched ({p.name})"
    if old not in src:
        sys.exit(f"[patch] ERROR: target block not found in {p.name}. "
                 f"File may already be modified or repo version differs.")
    p.write_text(src.replace(old, new, 1))
    return f"patched ({p.name})"

query_file, rbac_file = sys.argv[1], sys.argv[2]
SENTINEL = "_uuid.UUID(str(user.user_id))"

print(patch(query_file, QUERY_OLD, QUERY_NEW, SENTINEL))
print(patch(rbac_file,  RBAC_OLD,  RBAC_NEW,  SENTINEL))
PYEOF

ok "done."
log "backend uvicorn --reload should auto-pick up the change."
log "to force a restart anyway:"
log "  cd $REPO_DIR && docker compose -f docker-compose.dev.yml restart backend"
log "then tail logs:"
log "  docker logs -f aria-backend"
