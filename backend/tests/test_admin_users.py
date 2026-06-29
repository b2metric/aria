"""TIER 3 item 30 (follow-on b) — delete a user, propagating to Keycloak.

There was no user-delete route before; admins could create/edit users but never
remove them, so a deleted user's Keycloak account was orphaned. ``delete_user``
removes the local row AND deletes the Keycloak account by the stored
``external_id`` (best-effort: a KC outage must not block the local delete, and a
404 in KC is fine — the account is already gone). An admin cannot delete their
own account (would lock themselves out).

The users endpoints hit Postgres via the ORM; there is no DB test harness, so a
fake AsyncSession is injected directly and KeycloakAdminService is mocked.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from backend.app.api.endpoints.admin import users as users_api

pytestmark = pytest.mark.asyncio


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    """Minimal AsyncSession stand-in; ``scalars`` are returned by execute() in order."""

    def __init__(self, scalars):
        self._scalars = list(scalars)
        self.deleted: list = []
        self.committed = False

    async def execute(self, *a, **k):
        return _FakeResult(self._scalars.pop(0))

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.committed = True


class _AdminUser:
    can_admin = True
    workspace_id = "ws-acme"
    user_id = "admin-self-id"


def _mock_kc(monkeypatch, *, delete_raises=False):
    calls = {"deleted": []}

    class _FakeKC:
        def __init__(self, *a, **k):
            pass

        async def delete_user(self, kc_user_id):
            calls["deleted"].append(kc_user_id)
            if delete_raises:
                raise RuntimeError("keycloak unreachable")

    monkeypatch.setattr(users_api, "KeycloakAdminService", _FakeKC)
    return calls


def _make_user(*, customer_id, external_id="kc-user-1"):
    u = users_api.User(
        id=uuid.uuid4(),
        external_id=external_id,
        customer_id=customer_id,
        email="bob@acme.test",
        display_name="Bob",
        role="member",
    )
    return u


async def test_delete_user_removes_row_and_kc_account(monkeypatch):
    calls = _mock_kc(monkeypatch)
    customer_id = uuid.uuid4()
    user = _make_user(customer_id=customer_id, external_id="kc-user-abc")
    db = _FakeDB([customer_id, user])  # resolve_customer_id, then select(User)

    await users_api.delete_user(user_id=user.id, current_user=_AdminUser(), db=db)

    assert calls["deleted"] == ["kc-user-abc"]  # propagated by STORED external_id
    assert user in db.deleted
    assert db.committed


async def test_delete_user_404_when_not_in_customer(monkeypatch):
    _mock_kc(monkeypatch)
    customer_id = uuid.uuid4()
    db = _FakeDB([customer_id, None])  # select(User) → None (wrong customer / missing)

    with pytest.raises(HTTPException) as exc:
        await users_api.delete_user(user_id=uuid.uuid4(), current_user=_AdminUser(), db=db)

    assert exc.value.status_code == 404
    assert db.deleted == []


async def test_delete_user_is_resilient_when_keycloak_fails(monkeypatch):
    calls = _mock_kc(monkeypatch, delete_raises=True)
    customer_id = uuid.uuid4()
    user = _make_user(customer_id=customer_id)
    db = _FakeDB([customer_id, user])

    # KC outage must NOT block the local delete.
    await users_api.delete_user(user_id=user.id, current_user=_AdminUser(), db=db)

    assert calls["deleted"]  # attempted
    assert user in db.deleted
    assert db.committed


async def test_delete_user_skips_kc_when_no_external_id(monkeypatch):
    calls = _mock_kc(monkeypatch)
    customer_id = uuid.uuid4()
    user = _make_user(customer_id=customer_id, external_id=None)
    db = _FakeDB([customer_id, user])

    await users_api.delete_user(user_id=user.id, current_user=_AdminUser(), db=db)

    assert calls["deleted"] == []  # nothing linked in KC
    assert user in db.deleted


async def test_delete_user_refuses_self_delete(monkeypatch):
    calls = _mock_kc(monkeypatch)
    customer_id = uuid.uuid4()
    user = _make_user(customer_id=customer_id)
    user.id = uuid.UUID("00000000-0000-0000-0000-0000000000aa")

    admin = _AdminUser()
    admin.user_id = str(user.id)  # the admin IS this user
    db = _FakeDB([customer_id, user])

    with pytest.raises(HTTPException) as exc:
        await users_api.delete_user(user_id=user.id, current_user=admin, db=db)

    assert exc.value.status_code == 403
    assert db.deleted == []
    assert calls["deleted"] == []
