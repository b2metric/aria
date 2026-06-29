"""TIER 3 item 30 — teams are backed by a Keycloak group (kc_group_id).

create_team now creates a KC group and stores its id; delete_team deletes by that
STORED id (the old code passed the local team UUID, which was never a KC group id,
so the group was never actually deleted). KC outages must not block team CRUD.

The teams endpoints hit Postgres via the ORM; there is no DB test harness, so a
fake AsyncSession is injected directly (refresh() simulates the flush that
populates id/timestamps) and KeycloakAdminService is mocked.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from backend.app.api.endpoints.admin import teams as teams_api
from backend.app.schemas.organization import TeamCreate

pytestmark = pytest.mark.asyncio


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    """Minimal AsyncSession stand-in. ``scalars`` are returned by execute() in order."""

    def __init__(self, scalars):
        self._scalars = list(scalars)
        self.added: list = []
        self.deleted: list = []

    async def execute(self, *a, **k):
        return _FakeResult(self._scalars.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        # Simulate the DB flush that populates server-side defaults so the
        # endpoint's TeamResponse.model_validate(team) has id + timestamps.
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        now = datetime.utcnow()
        obj.created_at = getattr(obj, "created_at", None) or now
        obj.updated_at = getattr(obj, "updated_at", None) or now

    async def delete(self, obj):
        self.deleted.append(obj)


class _AdminUser:
    can_admin = True
    workspace_id = "ws-acme"


def _mock_kc(monkeypatch, *, group_id="kc-group-123", create_raises=False):
    calls = {"created": [], "deleted": []}

    class _FakeKC:
        def __init__(self, *a, **k):
            pass

        async def create_team_group(self, name):
            calls["created"].append(name)
            if create_raises:
                raise RuntimeError("keycloak unreachable")
            return group_id

        async def delete_team_group(self, gid):
            calls["deleted"].append(gid)

    monkeypatch.setattr(teams_api, "KeycloakAdminService", _FakeKC)
    return calls


async def test_create_team_creates_kc_group_and_stores_id(monkeypatch):
    calls = _mock_kc(monkeypatch, group_id="kc-group-abc")
    db = _FakeDB([uuid.uuid4()])  # resolve_customer_id → customer uuid

    resp = await teams_api.create_team(
        body=TeamCreate(name="Sales"), current_user=_AdminUser(), db=db
    )

    assert calls["created"] == ["Sales"]
    assert db.added[0].kc_group_id == "kc-group-abc"
    assert resp.id is not None


async def test_create_team_is_resilient_when_keycloak_fails(monkeypatch):
    _mock_kc(monkeypatch, create_raises=True)
    db = _FakeDB([uuid.uuid4()])

    resp = await teams_api.create_team(
        body=TeamCreate(name="Ops"), current_user=_AdminUser(), db=db
    )

    # Team still created, just without a linked KC group.
    assert db.added[0].kc_group_id is None
    assert resp.id is not None


async def test_delete_team_deletes_kc_group_by_stored_id(monkeypatch):
    calls = _mock_kc(monkeypatch)
    customer_id = uuid.uuid4()
    team = teams_api.Team(name="Sales", customer_id=customer_id)
    team.id = uuid.uuid4()
    team.kc_group_id = "kc-group-xyz"
    db = _FakeDB([customer_id, team])  # resolve_customer_id, then select(Team)

    await teams_api.delete_team(team_id=team.id, current_user=_AdminUser(), db=db)

    # Deleted by the STORED kc_group_id, NOT the local team.id.
    assert calls["deleted"] == ["kc-group-xyz"]
    assert team in db.deleted


async def test_delete_team_skips_kc_when_no_group_linked(monkeypatch):
    calls = _mock_kc(monkeypatch)
    customer_id = uuid.uuid4()
    team = teams_api.Team(name="Legacy", customer_id=customer_id)
    team.id = uuid.uuid4()
    team.kc_group_id = None  # pre-existing team with no KC group
    db = _FakeDB([customer_id, team])

    await teams_api.delete_team(team_id=team.id, current_user=_AdminUser(), db=db)

    assert calls["deleted"] == []  # nothing to delete in KC
    assert team in db.deleted  # local row still removed
