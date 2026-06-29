"""Item 25 — CSV export link must survive a conversation persistence round-trip.

Regression guard: previously `csv_url` was emitted only on the live SSE `chart`
event and never stored on the assistant `ConversationMessage`, so the CSV download
link vanished on F5 / history reload.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from backend.app.query import Conversation, ConversationMessage
from backend.app.query.conversation import (
    append_message,
    get_conversation,
    save_conversation,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def redis():
    r = FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


async def test_csv_url_survives_persistence_roundtrip(redis):
    conv = Conversation(workspace_id="ws", user_id="u")
    await save_conversation(redis, conv)
    await append_message(
        redis, "ws", conv.id, ConversationMessage(role="user", content="export the rows")
    )
    await append_message(
        redis,
        "ws",
        conv.id,
        ConversationMessage(
            role="assistant",
            content="Here is your data.",
            csv_url="https://minio.local/exports/abc.csv",
        ),
    )

    reloaded = await get_conversation(redis, "ws", conv.id)
    assert reloaded is not None
    assistant = [m for m in reloaded.messages if m.role == "assistant"][0]
    assert assistant.csv_url == "https://minio.local/exports/abc.csv"
