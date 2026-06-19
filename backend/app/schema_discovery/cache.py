"""Redis-backed schema cache with workspace-level tenant isolation.

Key pattern: ``aria:schema:{workspace_id}:{db_config_id}``

TTL defaults to 30 minutes, configurable via ``SCHEMA_CACHE_TTL`` env var.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from backend.app.core.config import get_settings
from backend.app.schema_discovery.models import SchemaSnapshot

if TYPE_CHECKING:
    from redis.asyncio import Redis


logger = logging.getLogger(__name__)

# ── Redis key prefix ───────────────────────────────────────────────────────
KEY_PREFIX = "aria:schema"


def _build_key(workspace_id: str, db_config_id: str) -> str:
    """Construct the Redis key for a schema snapshot.

    Tenant isolation is enforced via the workspace_id segment.
    """
    return f"{KEY_PREFIX}:{workspace_id}:{db_config_id}"


def _build_pattern(workspace_id: str) -> str:
    """Construct a key pattern that matches all schemas for a workspace."""
    return f"{KEY_PREFIX}:{workspace_id}:*"


# ── Connection management ──────────────────────────────────────────────────


async def _get_redis() -> Redis:
    """Return a connected Redis client using the configured URL."""
    settings = get_settings()
    return aioredis.from_url(
        str(settings.redis_url),
        decode_responses=True,
    )


# ── Public API ─────────────────────────────────────────────────────────────


async def get_schema(
    workspace_id: str,
    db_config_id: str,
) -> SchemaSnapshot | None:
    """Retrieve a cached schema snapshot.

    Returns ``None`` if the key doesn't exist or the TTL has expired.
    """
    r = await _get_redis()
    try:
        key = _build_key(workspace_id, db_config_id)
        raw = await r.get(key)
        if raw is None:
            logger.debug("Cache miss: %s", key)
            return None
        logger.debug("Cache hit: %s", key)
        data = json.loads(raw)
        return SchemaSnapshot(**data)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Corrupted cache entry for %s:%s: %s", workspace_id, db_config_id, exc)
        return None
    finally:
        await r.aclose()


async def set_schema(
    snapshot: SchemaSnapshot,
    ttl_seconds: int | None = None,
) -> None:
    """Store a schema snapshot in Redis.

    Args:
        snapshot: The schema snapshot to cache.
        ttl_seconds: Optional TTL override. If ``None``, uses
            ``SCHEMA_CACHE_TTL`` from settings (default 1800s / 30min).
    """
    if ttl_seconds is None:
        ttl_seconds = get_settings().schema_cache_ttl

    r = await _get_redis()
    try:
        key = _build_key(snapshot.workspace_id, snapshot.db_config_id)
        raw = snapshot.model_dump_json()
        await r.setex(key, ttl_seconds, raw)
        logger.info(
            "Cached schema %s:%s (%d tables, TTL=%ds)",
            snapshot.workspace_id,
            snapshot.db_config_id,
            snapshot.table_count,
            ttl_seconds,
        )
    finally:
        await r.aclose()


async def invalidate_schema(
    workspace_id: str,
    db_config_id: str,
) -> bool:
    """Delete a cached schema snapshot.

    Returns ``True`` if a key was deleted, ``False`` if none existed.
    """
    r = await _get_redis()
    try:
        key = _build_key(workspace_id, db_config_id)
        deleted = await r.delete(key)
        if deleted:
            logger.info("Invalidated schema cache: %s", key)
        return bool(deleted)
    finally:
        await r.aclose()


async def invalidate_workspace(workspace_id: str) -> int:
    """Delete all cached schemas for a workspace.

    Returns the number of keys deleted.
    """
    r = await _get_redis()
    try:
        pattern = _build_pattern(workspace_id)
        keys: list[str] = []
        cursor = 0
        while True:
            cursor, batch = await r.scan(cursor, match=pattern, count=100)
            keys.extend(batch)
            if cursor == 0:
                break
        if keys:
            deleted = await r.delete(*keys)
            logger.info(
                "Invalidated %d schema cache entries for workspace %s", deleted, workspace_id
            )
            return deleted
        return 0
    finally:
        await r.aclose()


async def get_cache_ttl(workspace_id: str, db_config_id: str) -> int:
    """Return the remaining TTL (seconds) for a cached schema.

    Returns ``-2`` if the key doesn't exist, ``-1`` if no expiry is set.
    """
    r = await _get_redis()
    try:
        key = _build_key(workspace_id, db_config_id)
        return await r.ttl(key)
    finally:
        await r.aclose()
