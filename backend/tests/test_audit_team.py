"""Unit tests for ``team_id`` attribution on query audit rows.

The dashboard needs to filter activity by team ("team/user bazlı da filtreleyip
görmek isterim").  These tests pin two pieces of that path:

  1. ``AuditService.log_event(..., team_id=<uuid>)`` records the team UUID on the
     persisted ``DataAuditLog`` entry (so ``GROUP BY team_id`` / equality filters
     work later).
  2. ``resolve_identity_uuid("platform")`` — the helper the pipeline uses to turn
     a (possibly non-UUID) group name into a stable UUID — is deterministic, so a
     team named "platform" always maps to the SAME team UUID.
"""

from __future__ import annotations

import uuid

import pytest

from backend.app.auth.identity import resolve_identity_uuid
from backend.app.services.audit import AuditService


class _FakeSession:
    """Captures the entry passed to ``add`` instead of touching the DB.

    Mirrors the fake-session style in ``test_sql_visibility.py``: ``commit`` is a
    no-op and ``add`` records the object so the test can assert on it.
    """

    def __init__(self) -> None:
        self.added: list = []
        self.committed = False

    def add(self, entry) -> None:
        self.added.append(entry)

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_log_event_sets_team_id_on_entry():
    session = _FakeSession()
    audit = AuditService(session)

    team_uuid = uuid.uuid4()
    entry = await audit.log_event(
        customer_id=uuid.uuid4(),
        action="query",
        resource_type="query",
        team_id=team_uuid,
    )

    assert entry.team_id == team_uuid
    assert session.added == [entry]
    assert session.committed is True


@pytest.mark.asyncio
async def test_log_event_team_id_defaults_to_none():
    session = _FakeSession()
    audit = AuditService(session)

    entry = await audit.log_event(
        customer_id=uuid.uuid4(),
        action="query",
        resource_type="query",
    )

    assert entry.team_id is None


def test_resolve_identity_uuid_platform_is_stable():
    # A non-UUID group name maps deterministically via uuid5 — the SAME name
    # always yields the SAME team UUID, so audit rows for "platform" group.
    first = resolve_identity_uuid("platform")
    second = resolve_identity_uuid("platform")

    assert isinstance(first, uuid.UUID)
    assert first == second
    # And a different group name maps somewhere else.
    assert resolve_identity_uuid("data-eng") != first
