"""TIER 3 item 21 — memory stats count by namespace via Qdrant scroll.

The old stats used literal ``{ws}:team:default`` / ``{ws}:user`` filters that
matched ~nothing. This pins the scroll-based classification by the namespaced
``user_id`` payload, scoped to the workspace.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock

from backend.app.memory.service import MemoryService


def _pt(uid: str, **extra):
    return types.SimpleNamespace(payload={"user_id": uid, **extra})


def test_get_memory_stats_classifies_by_namespace():
    svc = MemoryService.__new__(MemoryService)
    svc._memory = MagicMock()

    points = [
        _pt("ws1:alice"),
        _pt("ws1:bob"),  # 2 user
        _pt("ws1:team:sales"),  # 1 team
        _pt("ws1:query_cache"),  # 1 cache
        _pt("other:alice"),  # different workspace → ignored
        _pt("other:team:x"),  # ignored
    ]
    client = MagicMock()
    client.scroll.return_value = (points, None)  # single page (offset None ends loop)
    svc._qdrant_client = lambda: (client, "aria_memory")

    stats = svc.get_memory_stats("ws1")
    assert stats["by_type"] == {"user": 2, "team": 1, "cache": 1}
    assert stats["total"] == 4
