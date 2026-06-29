"""TIER 3 item 18 (Plan 2) — process_query(resume=True) must not re-append the
user message.

On a reconcile re-run (or any resume), the user's message was already persisted
by the original POST. Re-appending it would duplicate the turn in history. The
``resume`` flag gates the single user-message append; everything else (the
assistant turn) proceeds normally.

A chart-type-only question ("as a pie chart") is used so the deterministic
fast-path completes without an LLM/SQL round-trip.
"""

from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

import backend.app.query.conversation as conv_mod
from backend.app.query import Conversation, ConversationMessage, QueryRequest
from backend.app.query.pipeline import process_query

pytestmark = pytest.mark.asyncio


def _prior_messages() -> list[ConversationMessage]:
    return [
        ConversationMessage(role="user", content="revenue by region"),
        ConversationMessage(
            role="assistant",
            content="here",
            sql="SELECT region, revenue FROM sales",
            chart_spec={"type": "bar", "colors": ["#111111"]},
            chart_data=[{"region": "A", "revenue": 1}],
        ),
    ]


async def _drive(monkeypatch, *, resume: bool, conv: Conversation) -> list[ConversationMessage]:
    """Run process_query over *conv* and return the messages it appended."""
    r = FakeRedis(decode_responses=True)
    appended: list[ConversationMessage] = []

    async def fake_get_conversation(redis, ws, cid):
        return conv

    async def fake_save_conversation(redis, c):
        return None

    async def fake_append_message(redis, ws, cid, msg):
        appended.append(msg)
        conv.messages.append(msg)
        return conv

    monkeypatch.setattr(conv_mod, "get_conversation", fake_get_conversation)
    monkeypatch.setattr(conv_mod, "save_conversation", fake_save_conversation)
    monkeypatch.setattr(conv_mod, "append_message", fake_append_message)

    req = QueryRequest(question="as a pie chart", conversation_id="c1")
    events = [
        e
        async for e in process_query(
            redis=r,
            engine=None,
            request=req,
            workspace_id="ws-1",
            user_id="u1",
            team_id="t1",
            sql_visible=True,
            resume=resume,
        )
    ]
    # The fast-path always terminates with a done event.
    assert events[-1]["event"] == "done"
    return appended


async def test_initial_run_appends_user_message(monkeypatch):
    conv = Conversation(id="c1", workspace_id="ws-1", user_id="u1", messages=_prior_messages())
    appended = await _drive(monkeypatch, resume=False, conv=conv)
    user_appends = [m for m in appended if m.role == "user"]
    assert len(user_appends) == 1
    assert user_appends[0].content == "as a pie chart"


async def test_resume_does_not_reappend_user_message(monkeypatch):
    # On resume the user message is already the last persisted message.
    msgs = _prior_messages()
    msgs.append(ConversationMessage(role="user", content="as a pie chart"))
    conv = Conversation(id="c1", workspace_id="ws-1", user_id="u1", messages=msgs)

    appended = await _drive(monkeypatch, resume=True, conv=conv)

    user_appends = [m for m in appended if m.role == "user"]
    assert user_appends == []  # the user turn is NOT duplicated on resume
