"""Sync→async bridge for fire-and-forget metering from synchronous code paths.

Some metering call sites are synchronous — most notably mem0's ``embed()`` — but
the metering itself (``record_system_llm_usage``) is async and touches the DB +
Redis. Running it inline with ``asyncio.run`` is unsafe: the caller may already
hold a running event loop (``asyncio.run`` would raise), and blocking on it would
slow the caller. This module owns a single long-lived background event loop on a
daemon thread; sync callers submit a coroutine fire-and-forget, so metering never
blocks nor breaks the caller.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Return the shared background loop, starting it (once) if needed."""
    global _loop
    if _loop is not None and _loop.is_running():
        return _loop
    with _lock:
        if _loop is not None and _loop.is_running():
            return _loop
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=loop.run_forever, name="aria-metering-loop", daemon=True
        )
        thread.start()
        _loop = loop
        return loop


def submit_metering(coro: Coroutine[Any, Any, Any]) -> None:
    """Schedule ``coro`` on the background loop, fire-and-forget.

    Never raises into the caller. ``coro`` is expected to be best-effort (swallow
    its own errors); any that escape are logged. If the coroutine cannot be
    submitted at all, it is closed to avoid an "un-awaited coroutine" warning.
    """
    try:
        loop = _ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)

        def _log_exc(fut: Any) -> None:
            try:
                exc = fut.exception()
            except Exception:  # noqa: BLE001 — cancelled/timeout; nothing to log
                return
            if exc is not None:
                logger.warning("background metering failed: %s", exc)

        future.add_done_callback(_log_exc)
    except Exception:  # noqa: BLE001 — metering must never break the caller
        logger.exception("failed to submit metering coroutine")
        with contextlib.suppress(Exception):
            coro.close()
