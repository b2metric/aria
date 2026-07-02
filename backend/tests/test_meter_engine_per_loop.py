"""The system-metering engine must be per-event-loop.

``submit_metering`` runs ``record_system_llm_usage`` on a dedicated background
loop (``aria-metering-loop``), while vault retrieval awaits it inline on the
main loop. asyncpg connections are bound to the loop that created them, so a
single shared engine/pool used from both loops poisons the pool: checkout of a
foreign-loop connection dies with "got Future attached to a different loop"
(seen live as ``record_system_llm_usage failed for operation=vault_embedding``
plus "Exception terminating connection" noise). The invariant: each event loop
gets its own engine, cached within that loop.
"""

from __future__ import annotations

import asyncio

from backend.app.services import token as token_mod


async def _get_engine_once():
    return token_mod._get_meter_engine()


async def _get_engine_twice():
    return token_mod._get_meter_engine(), token_mod._get_meter_engine()


def test_meter_engine_differs_across_event_loops() -> None:
    eng_a = asyncio.run(_get_engine_once())  # loop A
    eng_b = asyncio.run(_get_engine_once())  # loop B
    assert eng_a is not eng_b, (
        "meter engine is shared across event loops — its asyncpg connections are "
        "loop-bound, so cross-loop pool reuse raises 'attached to a different loop'"
    )


def test_meter_engine_is_cached_within_one_loop() -> None:
    eng_1, eng_2 = asyncio.run(_get_engine_twice())
    assert eng_1 is eng_2, "meter engine must be created once per loop, not per call"
