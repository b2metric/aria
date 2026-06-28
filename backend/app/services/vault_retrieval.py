"""Semantic retrieval over the per-workspace vault.

Why this exists
---------------
``pipeline._generate_sql`` originally ranked tables by **bag-of-words keyword
overlap** between the user's question and each table's name / keyword list /
description. That worked for "show me sales by month" but failed on
analytical questions ("monthly recharge revenue bucket comparison") because
the right table (``FCT_PREP_RECHARGE``) shares no surface tokens with words
like "revenue", "bucket", "compare", while a less-relevant table
(``FCT_PREP_REV``) wins on the substring "REV".

This module replaces that signal with **cosine similarity in embedding space**:

- ``index_workspace_vault(workspace_id)`` embeds every ``*.md`` file in
  ``docs/vaults/<workspace>/tables/`` and upserts into a per-workspace Qdrant
  collection (``aria_vault_<workspace_id>``). It's idempotent — a SHA256 of
  the file's bytes is stored as payload, so a re-sync only re-embeds changed
  files.

- ``top_n_tables(workspace_id, question, n)`` embeds the question and returns
  ``[(table_name, score), ...]`` ordered by similarity. The pipeline uses this
  to re-order the table list **before** keyword scoring and the LLM call — so
  the model sees semantically-relevant tables first, within the
  ``ARIA_MAX_TABLES_IN_LLM`` cap.

Graceful degradation
--------------------
If Qdrant is unreachable or embedding fails, ``top_n_tables`` returns ``[]``
and the caller falls back to keyword scoring. No exception ever propagates.

Env vars
--------
- ``ARIA_EMBED_MODEL`` (default ``text-embedding-3-small``) — any LiteLLM-
  supported embedding model. For Gemini-only stacks, set to
  ``gemini/text-embedding-004`` (dim 768) and ``ARIA_EMBED_DIM=768``.
- ``ARIA_EMBED_DIM``   (default ``1536``) — must match the model's output dim.
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
_EMBED_INPUT_CHARS = 8000  # cap per-file input so we don't blow embedding token budget


def _collection_for(workspace_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in workspace_id)
    return f"aria_vault_{safe}"


def _vault_dir(workspace_id: str) -> pathlib.Path:
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
    return project_root / "docs" / "vaults" / workspace_id / "tables"


def _hash_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _point_id_for(table_name: str) -> int:
    """Deterministic int64 id from table name (so re-index updates same point)."""
    return int(hashlib.sha256(table_name.encode()).hexdigest()[:15], 16)


def _qdrant_client():
    from qdrant_client import QdrantClient

    from backend.app.core.config import get_settings

    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, timeout=10.0)


async def _embed(text: str) -> list[float]:
    """Embed a single text via LiteLLM proxy."""
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
    """Embed every md file in the workspace vault and upsert to Qdrant.

    Idempotent: a SHA256 hash of each file is stored in the point payload;
    files whose hash hasn't changed are skipped (no re-embedding).
    """
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

        # Skip if the stored point already has this hash
        try:
            existing = client.retrieve(
                collection_name=collection, ids=[pid], with_payload=True
            )
            if existing and existing[0].payload.get("hash") == file_hash:
                skipped += 1
                continue
        except Exception:
            pass  # treat as missing → embed

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
            logger.debug("Indexed %s in %s", table_name, collection)
        except Exception as e:
            failed += 1
            logger.warning("Failed to embed %s: %s", table_name, e)

    logger.info(
        "Vault index for %s: indexed=%d skipped=%d failed=%d total=%d",
        workspace_id,
        indexed,
        skipped,
        failed,
        len(md_files),
    )
    return {
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
        "total_md": len(md_files),
        "collection": collection,
    }


async def top_n_tables(
    workspace_id: str, question: str, n: int = 30
) -> list[tuple[str, float]]:
    """Return top-N table names by semantic similarity to the question.

    Returns ``[(table_name, score), ...]`` sorted descending by score.
    Returns ``[]`` on any error so the caller can fall back to keyword scoring.

    If the collection doesn't exist yet, this auto-triggers an initial
    ``index_workspace_vault`` — costly on first call, fast after that.
    """
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
        # qdrant-client >= 1.14 removed .search(); use .query_points().
        resp = client.query_points(
            collection_name=collection,
            query=vec,
            limit=n,
            with_payload=True,
        )
        return [(p.payload["table"], float(p.score)) for p in resp.points]
    except Exception as e:
        logger.warning("Qdrant query failed (%s); falling back", e)
        return []
