#!/bin/bash
# ============================================================================
# smoke/done-check.sh — Definition of Done gate (engineering-core:verification-before-completion).
# Run this BEFORE claiming any feature "done". It bundles, in one command, the gates a
# full-stack vertical slice must pass — so "I built the API" can't be mistaken for "done":
#   [1] backend tests pass (TDD)                         — HARD
#   [2] frontend tests pass (if frontend/ present)       — HARD
#   [3] API change must have a frontend surface          — WARN (API-with-no-UI smell)
#   [4] boot + login smoke (smoke/check.sh)              — HARD if stack reachable, else WARN
#
# Usage:  bash smoke/done-check.sh [base-ref]      (FE-coverage diff base; default origin/main)
# Exit:   0 = Done · 1 = not done (hard failure)
# ============================================================================
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
BASE="${1:-origin/main}"
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; NC='\033[0m'
hard=0; warn=0
pass(){ printf "  ${GRN}PASS${NC} %s\n" "$1"; }
bad(){  printf "  ${RED}FAIL${NC} %s\n" "$1"; hard=1; }
note(){ printf "  ${YEL}WARN${NC} %s\n" "$1"; warn=1; }

echo "━━━ Definition of Done — $(basename "$ROOT") ━━━"

git rev-parse --verify "$BASE" >/dev/null 2>&1 || BASE="HEAD~1"
changed=$( { git diff --name-only "$BASE"...HEAD 2>/dev/null; git diff --name-only 2>/dev/null; git diff --cached --name-only 2>/dev/null; } | sort -u )

echo "[1] Backend tests (TDD)"
if command -v uv >/dev/null 2>&1; then
  if uv run pytest -q >/tmp/doneck-pytest.log 2>&1; then pass "pytest green"
  else bad "pytest FAILED (/tmp/doneck-pytest.log)"; tail -6 /tmp/doneck-pytest.log | sed 's/^/      /'; fi
else
  note "uv not found — run backend tests manually"
fi

echo "[2] Frontend tests"
if [ -d frontend ] && [ -f frontend/package.json ]; then
  if ( cd frontend && npm run test --silent >/tmp/doneck-fe.log 2>&1 ); then pass "frontend tests green"
  else note "frontend tests failed/absent (/tmp/doneck-fe.log)"; fi
else
  pass "no frontend/ (skip)"
fi

echo "[3] Full-stack coverage (an API needs a UI surface)"
api_changed=$(printf '%s\n' "$changed" | grep -E '^backend/app/api/' | grep -vE '__init__|/deps' || true)
fe_changed=$(printf '%s\n' "$changed" | grep -E '^frontend/src/(app|components)/' || true)
if [ -n "$api_changed" ] && [ -z "$fe_changed" ]; then
  note "backend API changed but NO frontend surface — API-with-no-UI is INCOMPLETE; add the page/component:"
  printf '%s\n' "$api_changed" | head -5 | sed 's/^/        /'
else
  pass "API change paired with a frontend surface (or no API change)"
fi

echo "[4] Boot + login smoke"
if [ -x smoke/check.sh ]; then
  if curl -s -o /dev/null -m 3 "${SMOKE_BACKEND_URL:-http://api.aria.localhost}/health" 2>/dev/null; then
    if bash smoke/check.sh >/tmp/doneck-smoke.log 2>&1; then pass "smoke green"; else bad "smoke FAILED (/tmp/doneck-smoke.log)"; fi
  else
    note "stack not reachable — run 'bash smoke/check.sh' against the running stack before done"
  fi
else
  note "smoke/check.sh not found"
fi

echo "[5] Docs portal build (docs-site/)"
if [ -d docs-site ] && [ -f docs-site/package.json ]; then
  if [ -d docs-site/node_modules ]; then
    if ( cd docs-site && npm run build --silent >/tmp/doneck-docs.log 2>&1 ); then pass "docs build green"
    else note "docs build failed (/tmp/doneck-docs.log) — refresh via the aria-docs skill"; fi
  else
    note "docs-site deps not installed (cd docs-site && npm install) — docs build skipped"
  fi
else
  pass "no docs-site/ (skip)"
fi

echo ""
if [ "$hard" -eq 0 ]; then
  echo -e "${GRN}━━━ ✓ Definition of Done met ($warn warn) ━━━${NC}"; exit 0
fi
echo -e "${RED}━━━ ✗ NOT done — fix HARD failures above ($warn warn) ━━━${NC}"; exit 1
