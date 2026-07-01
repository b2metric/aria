#!/usr/bin/env python3
"""stc_reset_state.py — back up + wipe a workspace's SQL-generation state.

Clears everything that feeds ARIA's NL→SQL for one workspace so it starts from a
clean slate: mem0 memories (user prefs / team conventions / query cache), Redis
caches (schema discovery, conversations, saved queries, resumable runs) and the
vault's Qdrant embedding collection. The vault markdown enums / example queries
are NOT touched here — those are handled by rebuilding the .md files.

Runs from the HOST against the dev stack's published ports (qdrant 6333, redis
6380). Scoped to ONE workspace — other tenants are untouched.

    # backup only (Phase 0):
    uv run python scripts/stc_reset_state.py --workspace stc-kuwait --dump backups/mem0.json
    # wipe (Phase 4) — dumps first, then deletes:
    uv run python scripts/stc_reset_state.py --workspace stc-kuwait --dump backups/mem0.json --wipe

mem0 note: memories live in ONE shared Qdrant collection (aria_memory) multiplexed
by a ``user_id`` payload of the form ``<workspace>:<...>`` — Qdrant has no native
prefix-delete, so we scroll, match the prefix, and delete by id.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("stc-reset")


def _mem_points_for_workspace(client, collection: str, workspace: str) -> list:
    """Scroll the mem0 collection and return points whose user_id is workspace-scoped."""
    prefix = f"{workspace}:"
    matched: list = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            uid = str((p.payload or {}).get("user_id", ""))
            if uid.startswith(prefix):
                matched.append(p)
        if offset is None:
            break
    return matched


def _wipe_redis(redis_url: str, workspace: str) -> dict[str, int]:
    import redis

    r = redis.Redis.from_url(redis_url)
    patterns = [
        f"aria:schema:{workspace}:*",
        f"aria:conv:{workspace}:*",
        f"aria:conv_list:{workspace}:*",
        f"saved_queries:{workspace}:*",
        f"aria:run:{workspace}_*",
        f"aria:run_meta:{workspace}_*",
        f"aria:run_lock:{workspace}_*",
    ]
    deleted: dict[str, int] = {}
    for pat in patterns:
        keys = list(r.scan_iter(match=pat, count=500))
        if keys:
            r.delete(*keys)
        deleted[pat] = len(keys)
    return deleted


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backup + wipe a workspace's SQL-gen state.")
    p.add_argument("--workspace", required=True)
    p.add_argument("--qdrant-url", default="http://localhost:6333")
    p.add_argument("--redis-url", default="redis://localhost:6380/0")
    p.add_argument("--mem-collection", default="aria_memory")
    p.add_argument("--vault-collection", default=None,
                   help="Vault Qdrant collection (default aria_vault_<workspace>)")
    p.add_argument("--dump", help="Write matched mem0 points to this JSON path (backup)")
    p.add_argument("--wipe", action="store_true",
                   help="Delete mem0 points + redis keys + vault collection")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    from qdrant_client import QdrantClient

    vault_collection = args.vault_collection or f"aria_vault_{args.workspace}"
    client = QdrantClient(url=args.qdrant_url)

    # ── mem0: find workspace-scoped points ──
    try:
        matched = _mem_points_for_workspace(client, args.mem_collection, args.workspace)
    except Exception as e:  # noqa: BLE001
        logger.error("mem0 scroll failed on %s: %s", args.mem_collection, e)
        matched = []
    logger.info("mem0: %d point(s) scoped to '%s:'", len(matched), args.workspace)

    if args.dump:
        out = Path(args.dump)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                [{"id": str(p.id), "payload": p.payload} for p in matched],
                indent=2, ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info("dumped %d mem0 point(s) → %s", len(matched), out)

    if not args.wipe:
        logger.info("dry/backup only (no --wipe). Done.")
        return 0

    # ── wipe mem0 points ──
    if matched:
        client.delete(
            collection_name=args.mem_collection,
            points_selector=[p.id for p in matched],
        )
        logger.info("deleted %d mem0 point(s) from %s", len(matched), args.mem_collection)

    # ── wipe redis caches ──
    try:
        deleted = _wipe_redis(args.redis_url, args.workspace)
        logger.info("redis keys deleted: %s", deleted)
    except Exception as e:  # noqa: BLE001
        logger.error("redis wipe failed: %s", e)

    # ── drop vault Qdrant collection (rebuilt by index_workspace_vault) ──
    try:
        if client.collection_exists(vault_collection):
            client.delete_collection(vault_collection)
            logger.info("dropped vault collection %s", vault_collection)
        else:
            logger.info("vault collection %s absent (nothing to drop)", vault_collection)
    except Exception as e:  # noqa: BLE001
        logger.error("vault collection drop failed: %s", e)

    logger.info("wipe complete for '%s'", args.workspace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
