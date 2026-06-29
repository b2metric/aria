"""TIER 2 item 14 — saved-queries store (Redis).

The dashboard surfaced a hardcoded ``savedQueries: []`` with no save logic; this
pins the new save/list/delete store (newest-first, per workspace+user isolated).
"""

from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from backend.app.query.saved_queries import (
    delete_saved_query,
    list_saved_queries,
    save_query,
)


@pytest.mark.asyncio
async def test_save_list_delete_roundtrip():
    r = FakeRedis(decode_responses=True)
    e1 = await save_query(
        r, workspace_id="ws1", user_id="u1", question="revenue by region", sql="SELECT 1"
    )
    e2 = await save_query(
        r, workspace_id="ws1", user_id="u1", question="top customers", sql="SELECT 2", name="Top"
    )

    items = await list_saved_queries(r, workspace_id="ws1", user_id="u1")
    assert [i["question"] for i in items] == ["top customers", "revenue by region"]  # newest first
    assert items[0]["name"] == "Top"

    # Per-user isolation.
    assert await list_saved_queries(r, workspace_id="ws1", user_id="other") == []

    # Delete by id.
    assert await delete_saved_query(r, workspace_id="ws1", user_id="u1", query_id=e1["id"]) is True
    assert await delete_saved_query(r, workspace_id="ws1", user_id="u1", query_id="nope") is False
    remaining = await list_saved_queries(r, workspace_id="ws1", user_id="u1")
    assert [i["id"] for i in remaining] == [e2["id"]]
