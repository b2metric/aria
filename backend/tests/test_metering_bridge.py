"""Task 17: the sync→async metering bridge.

``submit_metering`` lets synchronous code (e.g. mem0's ``embed()``) fire a
metering coroutine onto a shared background event loop without holding/needing a
loop itself, and without ever raising into the caller.
"""

from __future__ import annotations

import threading

from backend.app.services.metering_bridge import submit_metering


def test_submit_metering_runs_coroutine_on_background_loop() -> None:
    ran = threading.Event()

    async def _work() -> None:
        ran.set()

    submit_metering(_work())
    assert ran.wait(timeout=3.0), "coroutine was not run on the background loop"


def test_submit_metering_swallows_coroutine_errors() -> None:
    ran = threading.Event()

    async def _boom() -> None:
        ran.set()
        raise RuntimeError("metering blew up")

    # Must not raise into the caller; the error is logged on the background loop.
    submit_metering(_boom())
    assert ran.wait(timeout=3.0)
