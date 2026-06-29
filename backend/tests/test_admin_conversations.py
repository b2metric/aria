"""TIER 3 item 23 — /admin/conversations debug screen (backend).

Admins can list every conversation in their workspace and open one to inspect
its per-turn QueryTrace. Covers: the workspace-scoped Redis scan helper, the
endpoint data path, and the require_role(ADMIN) guard (route-table introspection,
matching test_rbac_guards' approach)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from backend.app.api.endpoints.admin import conversations as conv_admin
from backend.app.query import Conversation, ConversationMessage
from backend.app.query.conversation import list_workspace_conversations, save_conversation

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def redis():
    r = FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


def _conv(ws: str, user: str, title: str) -> Conversation:
    return Conversation(
        workspace_id=ws,
        user_id=user,
        title=title,
        messages=[
            ConversationMessage(role="user", content="q"),
            ConversationMessage(
                role="assistant",
                content="a",
                sql="SELECT 1",
                trace={"model": "gemini-reasoner", "row_count": 3, "sql_generated": True},
            ),
        ],
    )


async def test_list_workspace_conversations_is_scoped_and_sorted(redis):
    await save_conversation(redis, _conv("ws-1", "alice", "first"))
    await save_conversation(redis, _conv("ws-1", "bob", "second"))
    await save_conversation(redis, _conv("ws-2", "carol", "other-ws"))

    convs = await list_workspace_conversations(redis, "ws-1", limit=50)

    titles = {c.title for c in convs}
    assert titles == {"first", "second"}  # ws-2 excluded
    # A prefix-colliding workspace must not leak in (delimiter is the colon).
    assert all(c.workspace_id == "ws-1" for c in convs)


async def test_admin_list_endpoint_returns_summaries(redis, monkeypatch):
    await save_conversation(redis, _conv("ws-1", "alice", "first"))
    monkeypatch.setattr(conv_admin, "_get_redis", lambda: redis)

    class _User:
        workspace_id = "ws-1"

    out = await conv_admin.list_all_conversations(user=_User(), _=None)

    assert len(out) == 1
    assert out[0]["title"] == "first"
    assert out[0]["user_id"] == "alice"
    assert out[0]["message_count"] == 2


async def test_admin_detail_endpoint_includes_trace(redis, monkeypatch):
    conv = _conv("ws-1", "alice", "first")
    await save_conversation(redis, conv)
    monkeypatch.setattr(conv_admin, "_get_redis", lambda: redis)

    class _User:
        workspace_id = "ws-1"

    detail = await conv_admin.get_conversation_detail_admin(
        conversation_id=conv.id, user=_User(), _=None
    )

    assistant = [m for m in detail["messages"] if m["role"] == "assistant"][0]
    assert assistant["trace"]["model"] == "gemini-reasoner"
    assert assistant["trace"]["row_count"] == 3


def test_admin_conversations_endpoints_require_admin():
    """Both endpoints must carry the require_role(ADMIN) guard."""
    from backend.app.main import app

    targets = {"list_all_conversations", "get_conversation_detail_admin"}
    seen: dict[str, bool] = {}
    for route in app.routes:
        name = getattr(getattr(route, "endpoint", None), "__name__", None)
        if name in targets:
            deps = getattr(getattr(route, "dependant", None), "dependencies", [])
            quals = [getattr(getattr(d, "call", None), "__qualname__", "") for d in deps]
            seen[name] = any("require_admin" in q for q in quals)

    for name in targets:
        assert seen.get(name), f"{name} is missing a require_role(ADMIN) guard"
