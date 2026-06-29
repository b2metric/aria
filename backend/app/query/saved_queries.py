"""Saved queries — let users bookmark a question+SQL for re-use.

TIER 2 item 14: the dashboard surfaced a hardcoded ``savedQueries: []`` with no
save endpoint anywhere. This is a small Redis-backed store (mirrors how
conversations live in Redis) keyed per workspace+user.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

_MAX_SAVED = 100


def _key(workspace_id: str, user_id: str) -> str:
    return f"saved_queries:{workspace_id}:{user_id}"


async def save_query(
    redis: Redis,
    *,
    workspace_id: str,
    user_id: str,
    question: str,
    sql: str,
    name: str | None = None,
) -> dict[str, Any]:
    """Persist a saved query and return it. Newest first; capped at _MAX_SAVED."""
    entry = {
        "id": uuid.uuid4().hex,
        "name": name or (question[:60] if question else "Saved query"),
        "question": question,
        "sql": sql,
        "created_at": datetime.now(UTC).isoformat(),
    }
    key = _key(workspace_id, user_id)
    await redis.lpush(key, json.dumps(entry))
    await redis.ltrim(key, 0, _MAX_SAVED - 1)
    return entry


async def list_saved_queries(
    redis: Redis, *, workspace_id: str, user_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Return the user's saved queries, newest first."""
    raw = await redis.lrange(_key(workspace_id, user_id), 0, limit - 1)
    out: list[dict[str, Any]] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            continue
    return out


async def delete_saved_query(
    redis: Redis, *, workspace_id: str, user_id: str, query_id: str
) -> bool:
    """Delete one saved query by id. Returns True if an entry was removed."""
    key = _key(workspace_id, user_id)
    for item in await redis.lrange(key, 0, -1):
        try:
            if json.loads(item).get("id") == query_id:
                await redis.lrem(key, 1, item)
                return True
        except (json.JSONDecodeError, TypeError):
            continue
    return False
