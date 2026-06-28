#!/usr/bin/env bash
# patch-vault-semantic-retrieval.sh — wire Qdrant-based semantic table retrieval
# into the SQL generation pipeline.
#
# WHY: keyword bag-of-words ranking picks the wrong table when the question and
# the table name don't share surface tokens (e.g. "monthly recharge revenue
# bucket comparison" vs FCT_PREP_RECHARGE — they don't share "revenue").
# Embedding similarity does. Qdrant is already running in the stack; this just
# uses it for the vault too (separate collection from mem0).
#
# This patch:
#   1) Creates backend/app/services/vault_retrieval.py
#      - index_workspace_vault(): embeds every *.md under the workspace's vault
#        and upserts to Qdrant collection `aria_vault_<workspace_id>`.
#        Idempotent via per-file SHA256 hash.
#      - top_n_tables(): embeds the question, returns top-N table names by
#        cosine similarity. Returns [] on any error → caller keyword-falls-back.
#   2) Patches backend/app/query/pipeline.py:_generate_sql to:
#      - call top_n_tables BEFORE column-fetch and re-rank `tables` accordingly
#      - replace both hardcoded `tables[:10]` with env-controlled ARIA_MAX_TABLES_IN_LLM
#   3) Patches backend/app/services/vault_sync.py:sync() to call
#      index_workspace_vault() after schema sync — embeddings stay fresh
#      whenever the vault is re-synced.
#
# Env vars (defaults are sane — set only to override):
#   ARIA_EMBED_MODEL   default text-embedding-3-small (1536 dim)
#                      for Gemini-only stacks use gemini/text-embedding-004
#   ARIA_EMBED_DIM     default 1536  (set to 768 for gemini/text-embedding-004)
#
# Idempotent. Run from the repo root (~/projects/b2metric-aria by default).
#
# Usage:
#   bash scripts/patch-vault-semantic-retrieval.sh
#   docker compose -f docker-compose.dev.yml restart backend
#   # then trigger an initial index (will auto-run on first query too):
#   docker logs -f aria-backend   # look for "Created vault collection ... " / "Indexed ..."

set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
RETRIEVAL_FILE="$REPO_DIR/backend/app/services/vault_retrieval.py"
PIPELINE_FILE="$REPO_DIR/backend/app/query/pipeline.py"
SYNC_FILE="$REPO_DIR/backend/app/services/vault_sync.py"

log() { printf '\033[36m[patch]\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m[patch]\033[0m %s\n' "$*"; }
warn(){ printf '\033[33m[patch]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[patch]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f "$PIPELINE_FILE" ]] || die "not found: $PIPELINE_FILE  (run from repo root)"
[[ -f "$SYNC_FILE"     ]] || die "not found: $SYNC_FILE"

# ── 1. Write vault_retrieval.py (idempotent: skip if sentinel found) ──────────
RETRIEVAL_SENTINEL='async def top_n_tables('
if [[ -f "$RETRIEVAL_FILE" ]] && grep -q "$RETRIEVAL_SENTINEL" "$RETRIEVAL_FILE"; then
  log "already present ($(basename "$RETRIEVAL_FILE"))"
else
  log "creating $(basename "$RETRIEVAL_FILE")"
  cat >"$RETRIEVAL_FILE" <<'PYEOF'
"""Semantic retrieval over the per-workspace vault.

Embeds each table-level markdown file into a per-workspace Qdrant collection
(aria_vault_<workspace_id>) and exposes top_n_tables() for the SQL pipeline
to re-rank tables by cosine similarity to the user's question — replacing the
old bag-of-words keyword scoring that misses semantically-relevant tables
whose name doesn't share surface tokens with the question.

Graceful degradation: any failure (Qdrant unreachable, embedding error,
missing collection) returns [] so the caller can fall back to keyword scoring.

Env vars:
  ARIA_EMBED_MODEL  default text-embedding-3-small (any LiteLLM-supported model)
  ARIA_EMBED_DIM    default 1536  (must match the model's output dim)
"""

from __future__ import annotations

import hashlib
import logging
import os
import pathlib
from typing import Any

logger = logging.getLogger(__name__)

_EMBED_MODEL = os.environ.get("ARIA_EMBED_MODEL", "text-embedding-3-small")
_EMBED_DIM = int(os.environ.get("ARIA_EMBED_DIM", "1536"))
_EMBED_INPUT_CHARS = 8000


def _collection_for(workspace_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in workspace_id)
    return f"aria_vault_{safe}"


def _vault_dir(workspace_id: str) -> pathlib.Path:
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
    return project_root / "docs" / "vaults" / workspace_id / "tables"


def _hash_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _point_id_for(table_name: str) -> int:
    return int(hashlib.sha256(table_name.encode()).hexdigest()[:15], 16)


def _qdrant_client():
    from qdrant_client import QdrantClient

    from backend.app.core.config import get_settings

    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, timeout=10.0)


async def _embed(text: str) -> list[float]:
    import litellm

    from backend.app.core.config import get_settings

    settings = get_settings()
    resp = await litellm.aembedding(
        model=_EMBED_MODEL,
        input=[text],
        api_base=settings.litellm_api_base,
        api_key=settings.litellm_api_key or "sk-dummy",
        timeout=20.0,
    )
    return resp.data[0]["embedding"]


async def index_workspace_vault(workspace_id: str) -> dict[str, Any]:
    from qdrant_client import models

    vault_dir = _vault_dir(workspace_id)
    if not vault_dir.exists():
        logger.warning("Vault dir missing: %s", vault_dir)
        return {"indexed": 0, "skipped": 0, "reason": "vault_dir_missing"}

    md_files = sorted(vault_dir.glob("*.md"))
    if not md_files:
        return {"indexed": 0, "skipped": 0, "reason": "no_md_files"}

    try:
        client = _qdrant_client()
    except Exception as e:
        logger.warning("Qdrant unreachable, skipping vault index: %s", e)
        return {"indexed": 0, "skipped": 0, "reason": "qdrant_unreachable"}

    collection = _collection_for(workspace_id)
    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=_EMBED_DIM, distance=models.Distance.COSINE
            ),
        )
        logger.info("Created vault collection: %s (dim=%d)", collection, _EMBED_DIM)

    indexed, skipped, failed = 0, 0, 0
    for md in md_files:
        table_name = md.stem
        file_hash = _hash_file(md)
        pid = _point_id_for(table_name)

        try:
            existing = client.retrieve(
                collection_name=collection, ids=[pid], with_payload=True
            )
            if existing and existing[0].payload.get("hash") == file_hash:
                skipped += 1
                continue
        except Exception:
            pass

        try:
            content = md.read_text()[:_EMBED_INPUT_CHARS]
            vec = await _embed(content)
            client.upsert(
                collection_name=collection,
                points=[
                    models.PointStruct(
                        id=pid,
                        vector=vec,
                        payload={
                            "table": table_name,
                            "hash": file_hash,
                            "path": str(md.relative_to(vault_dir.parent.parent.parent)),
                        },
                    )
                ],
            )
            indexed += 1
        except Exception as e:
            failed += 1
            logger.warning("Failed to embed %s: %s", table_name, e)

    logger.info(
        "Vault index for %s: indexed=%d skipped=%d failed=%d total=%d",
        workspace_id, indexed, skipped, failed, len(md_files),
    )
    return {
        "indexed": indexed, "skipped": skipped, "failed": failed,
        "total_md": len(md_files), "collection": collection,
    }


async def top_n_tables(
    workspace_id: str, question: str, n: int = 30
) -> list[tuple[str, float]]:
    """Return top-N table names by semantic similarity. Returns [] on any error."""
    try:
        client = _qdrant_client()
    except Exception as e:
        logger.debug("Qdrant unreachable for top_n_tables: %s", e)
        return []

    collection = _collection_for(workspace_id)
    try:
        if not client.collection_exists(collection):
            logger.info("Auto-indexing vault on first retrieval call: %s", workspace_id)
            res = await index_workspace_vault(workspace_id)
            if res.get("indexed", 0) == 0 and res.get("skipped", 0) == 0:
                return []
    except Exception as e:
        logger.warning("collection_exists check failed: %s", e)
        return []

    try:
        vec = await _embed(question)
    except Exception as e:
        logger.warning("Embedding the question failed (%s); skipping semantic rerank", e)
        return []

    try:
        hits = client.search(
            collection_name=collection, query_vector=vec, limit=n, with_payload=True,
        )
        return [(h.payload["table"], float(h.score)) for h in hits]
    except Exception as e:
        logger.warning("Qdrant search failed (%s); falling back", e)
        return []
PYEOF
  ok "wrote $(basename "$RETRIEVAL_FILE")"
fi

# ── 2. Patch pipeline.py + vault_sync.py ──────────────────────────────────────
python3 - "$PIPELINE_FILE" "$SYNC_FILE" <<'PYEOF'
import sys, pathlib

PIPELINE_OLD = '''    # Get columns for each table (up to 10 tables for performance)
    # Get columns for each table (up to 10 tables for performance)
    table_columns: dict[str, list[dict]] = {}
    schema_info: list[str] = []
    for tbl in tables[:10]:
        cols = await _get_table_columns(engine, tbl["name"], workspace_id)
        table_columns[tbl["name"]] = cols'''

PIPELINE_NEW = '''    # ── Semantic re-rank (Qdrant) before column fetch ───────────────────────
    # If the workspace has its vault embedded into Qdrant, ask which tables are
    # closest to the user\'s question and re-order `tables` accordingly. The
    # column-fetch limit below then picks the SEMANTICALLY relevant top-N
    # instead of whatever order the vault traversal returned. Falls back
    # silently to the existing order if Qdrant is down or the collection
    # doesn\'t exist yet (the next call auto-indexes).
    try:
        from backend.app.services.vault_retrieval import top_n_tables

        semantic_ranked = await top_n_tables(workspace_id, question, n=30)
        if semantic_ranked:
            rank_map = {name: i for i, (name, _) in enumerate(semantic_ranked)}
            tables.sort(key=lambda t: rank_map.get(t["name"], 999))
            logger.info(
                "Semantic re-rank applied for workspace=%s (top3=%s)",
                workspace_id,
                [r[0] for r in semantic_ranked[:3]],
            )
    except Exception as _rerank_err:
        logger.warning("Semantic rerank skipped: %s", _rerank_err)

    # Get columns for the top-N most relevant tables. Capped by
    # ARIA_MAX_TABLES_IN_LLM so the LLM schema slice and column-fetch agree.
    import os as _os_pipe

    _max_tables_for_columns = int(_os_pipe.environ.get("ARIA_MAX_TABLES_IN_LLM", "30"))
    table_columns: dict[str, list[dict]] = {}
    schema_info: list[str] = []
    for tbl in tables[:_max_tables_for_columns]:
        cols = await _get_table_columns(engine, tbl["name"], workspace_id)
        table_columns[tbl["name"]] = cols'''

PIPELINE_OLD2 = '''    for tbl in tables[:10]:
        cols = table_columns.get(tbl["name"], [])
        col_str = ", ".join(f"{c[\'name\']} ({c[\'type\']})" for c in cols[:15])
        schema_info.append(f"  {tbl[\'name\']}: {col_str}")'''

PIPELINE_NEW2 = '''    for tbl in tables[:_max_tables_for_columns]:
        cols = table_columns.get(tbl["name"], [])
        col_str = ", ".join(f"{c[\'name\']} ({c[\'type\']})" for c in cols[:15])
        schema_info.append(f"  {tbl[\'name\']}: {col_str}")'''

PIPELINE_SENTINEL = 'Semantic re-rank applied for workspace'

SYNC_OLD = '''            # 3b. Inject sampled enum-value block (idempotent — skips if unchanged).
            table_enums = enum_map.get(table_name)
            if table_enums:
                file_path = self.vault_path / f"{table_name}.md"
                if inject_enum_block(file_path, table_enums):
                    stats["enum_updated"] += 1

        return stats'''

SYNC_NEW = '''            # 3b. Inject sampled enum-value block (idempotent — skips if unchanged).
            table_enums = enum_map.get(table_name)
            if table_enums:
                file_path = self.vault_path / f"{table_name}.md"
                if inject_enum_block(file_path, table_enums):
                    stats["enum_updated"] += 1

        # 4. Refresh Qdrant embeddings for the workspace\'s vault so semantic
        # table retrieval stays in sync with the (just-updated) md files.
        # Best-effort — sync still succeeds even if Qdrant or the embedding
        # endpoint is unreachable.
        try:
            from backend.app.services.vault_retrieval import index_workspace_vault

            embed_stats = await index_workspace_vault(self.workspace_id)
            stats["embeddings"] = embed_stats
        except Exception as e:
            logger.warning("Vault embedding refresh failed: %s", e)
            stats["embeddings"] = {"error": str(e)}

        return stats'''

SYNC_SENTINEL = 'Vault embedding refresh failed'

pipe, sync = sys.argv[1], sys.argv[2]
src = pathlib.Path(pipe).read_text()
if PIPELINE_SENTINEL in src:
    print("already patched (pipeline.py)")
else:
    if PIPELINE_OLD not in src:
        sys.exit("[patch] ERROR: pipeline.py first target block not found.")
    if PIPELINE_OLD2 not in src:
        sys.exit("[patch] ERROR: pipeline.py second target block not found.")
    src = src.replace(PIPELINE_OLD, PIPELINE_NEW, 1)
    src = src.replace(PIPELINE_OLD2, PIPELINE_NEW2, 1)
    pathlib.Path(pipe).write_text(src)
    print("patched (pipeline.py)")

src = pathlib.Path(sync).read_text()
if SYNC_SENTINEL in src:
    print("already patched (vault_sync.py)")
elif SYNC_OLD not in src:
    sys.exit("[patch] ERROR: vault_sync.py target block not found.")
else:
    pathlib.Path(sync).write_text(src.replace(SYNC_OLD, SYNC_NEW, 1))
    print("patched (vault_sync.py)")
PYEOF

ok "all patches applied."
log "restart backend:"
log "  cd $REPO_DIR && docker compose -f docker-compose.dev.yml restart backend"
log ""
log "verify on first query — tail logs for these lines:"
log "  Auto-indexing vault on first retrieval call: <workspace>"
log "  Created vault collection: aria_vault_<workspace> (dim=1536)"
log "  Vault index for <workspace>: indexed=N skipped=0 failed=0 total=N"
log "  Semantic re-rank applied for workspace=<ws> (top3=[...])"
log ""
log "if you don't have OpenAI tokens, switch to Gemini embeddings:"
log "  echo 'ARIA_EMBED_MODEL=gemini/text-embedding-004' >> backend/.env"
log "  echo 'ARIA_EMBED_DIM=768' >> backend/.env"
log "  docker compose -f docker-compose.dev.yml restart backend"
