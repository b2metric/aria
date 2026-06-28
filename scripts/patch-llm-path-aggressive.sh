#!/usr/bin/env bash
# patch-llm-path-aggressive.sh — push more questions to LLM path + widen schema slice.
#
# WHY: the rule-based SQL generator picks ONE table by keyword overlap and slaps
# SUM(first_numeric_column) GROUP BY date on it. That's fine for "total sales by
# month" but wrong for anything analytical (MoM, bucket analysis, growth %, JOIN).
# Also, the LLM fallback only ever saw the first 10 tables — the right table was
# routinely dropped from context before the model could see it.
#
# This patch:
#   1) Lowers the rule-based gate (score < 30 instead of < 15) AND triggers the
#      LLM path whenever is_complex_query() matches (MoM/compare/growth/etc.).
#   2) Raises the schema-context cap from 10 → 30 tables.
#
# Both are env-tunable on the deployed container:
#   ARIA_KEYWORD_SCORE_THRESHOLD=30   (default after this patch)
#   ARIA_MAX_TABLES_IN_LLM=30         (default after this patch)
#
# Idempotent. Run from the repo root (~/projects/b2metric-aria by default).
#
# Usage:
#   bash scripts/patch-llm-path-aggressive.sh
#   docker compose -f docker-compose.dev.yml restart backend
#   docker logs -f aria-backend

set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PIPELINE_FILE="$REPO_DIR/backend/app/query/pipeline.py"
LLM_SQL_FILE="$REPO_DIR/backend/app/query/llm_sql.py"

log() { printf '\033[36m[patch]\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m[patch]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[patch]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f "$PIPELINE_FILE" ]] || die "not found: $PIPELINE_FILE  (run from repo root or pass repo dir as arg)"
[[ -f "$LLM_SQL_FILE"  ]] || die "not found: $LLM_SQL_FILE"

python3 - "$PIPELINE_FILE" "$LLM_SQL_FILE" <<'PYEOF'
import sys, pathlib

# ── pipeline.py ───────────────────────────────────────────────────────────────
PIPELINE_OLD = '''    # If score is too low, our simple lexical heuristic failed to find a confident match
    # This means the question requires semantic understanding (e.g. synonyms, cross-language)
    # Forward to LLM instead of guessing blindly.
    if best_score < 15:
        from backend.app.query.llm_sql import generate_sql_with_llm

        logger.info(
            "Low confidence in rule-based table selection (score=%d). Delegating to LLM.",
            best_score,
        )'''

PIPELINE_NEW = '''    # If score is too low OR the question is structurally complex (MoM, bucket,
    # compare, growth, JOIN, subquery, window), forward to LLM. The old rule-based
    # path picks ONE table by keyword overlap and slaps SUM(first_numeric) GROUP BY
    # date on it — fine for "total sales by month", wrong for anything analytical.
    # Threshold + complex-question gate are env-configurable so we can tune without
    # a code change.
    import os as _os

    from backend.app.query.llm_sql import generate_sql_with_llm, is_complex_query

    keyword_threshold = int(_os.environ.get("ARIA_KEYWORD_SCORE_THRESHOLD", "30"))
    is_complex = is_complex_query(question)
    force_llm = best_score < keyword_threshold or is_complex
    if force_llm:
        logger.info(
            "Delegating to LLM (score=%d, threshold=%d, complex=%s)",
            best_score,
            keyword_threshold,
            is_complex,
        )'''

PIPELINE_SENTINEL = 'ARIA_KEYWORD_SCORE_THRESHOLD'

# ── llm_sql.py ────────────────────────────────────────────────────────────────
LLM_OLD = '''    parts = ["Available tables and columns:"]
    for tbl in tables[:10]:  # Limit to 10 tables'''

LLM_NEW = '''    import os

    # ARIA_MAX_TABLES_IN_LLM caps the schema slice handed to the LLM. The old
    # hard-coded 10 was tight for vaults with 20-40 tables (e.g. STC), causing
    # the correct table to be dropped from context before the model ever saw it.
    # Bump to 30 by default; tune higher only if prompts become token-heavy.
    max_tables = int(os.environ.get("ARIA_MAX_TABLES_IN_LLM", "30"))
    parts = ["Available tables and columns:"]
    for tbl in tables[:max_tables]:'''

LLM_SENTINEL = 'ARIA_MAX_TABLES_IN_LLM'

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

pipe, llm = sys.argv[1], sys.argv[2]
print(patch(pipe, PIPELINE_OLD, PIPELINE_NEW, PIPELINE_SENTINEL))
print(patch(llm,  LLM_OLD,      LLM_NEW,      LLM_SENTINEL))
PYEOF

ok "code patched."
log "no env-var change needed — defaults are 30 / 30 after this patch."
log "to OVERRIDE on a deployed container, add to backend/.env:"
log "  ARIA_KEYWORD_SCORE_THRESHOLD=30"
log "  ARIA_MAX_TABLES_IN_LLM=30"
log ""
log "restart backend to pick up code (uvicorn --reload should auto-pick up):"
log "  cd $REPO_DIR && docker compose -f docker-compose.dev.yml restart backend"
log "tail logs to see the new 'Delegating to LLM (score=N, threshold=30, complex=True)' lines:"
log "  docker logs -f aria-backend"
