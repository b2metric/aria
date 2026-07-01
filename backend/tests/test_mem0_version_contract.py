"""MECHANICAL GATE (model-independent, CI-blocking) for the mem0 version contract.

The memory service is written against the mem0 **2.x** API (scope goes inside
``filters={"user_id": ...}`` — see backend/app/memory/service.py). A past incident
had the container pinned to mem0 0.1.116 (the ``user_id=`` API) while pyproject
resolved a newer major — code written for one API broke on the other.

This test pins the contract to pyproject's ``mem0ai>=2.0.1,<3`` so ANY drift
(downgrade, or a container image built off a stale lock) fails loudly wherever the
suite runs — including a container smoke — instead of surfacing as a runtime
"parameter not supported" error deep in memory recall. If mem0 is intentionally
bumped to a new major, update BOTH this bound and the ``filters=``/``user_id=`` call
sites in memory/service.py together.
"""

from __future__ import annotations

from importlib.metadata import version

from packaging.version import Version

MIN_INCLUSIVE = Version("2.0.1")  # CVE-2026-7597 floor (see pyproject)
MAX_EXCLUSIVE = Version("3")      # 2.x API surface (filters=…) the code targets


def test_installed_mem0_matches_pinned_major() -> None:
    installed = Version(version("mem0ai"))
    assert MIN_INCLUSIVE <= installed < MAX_EXCLUSIVE, (
        f"mem0ai {installed} is outside the supported range "
        f"[{MIN_INCLUSIVE}, {MAX_EXCLUSIVE}). The memory service targets the mem0 2.x "
        "API (filters={'user_id': ...}); a drifted install will raise at recall time. "
        "Rebuild the image / fix the pin, or bump the code + this bound together."
    )
