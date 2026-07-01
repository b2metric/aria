"""Sprint 2.5 Task 14: LiteLLM call attribution helper (user + metadata.tags)."""

from __future__ import annotations

from backend.app.services.litellm_meta import litellm_meta, litellm_tags


def _tag_set(m: dict) -> set[str]:
    return set(m["extra_headers"]["x-litellm-tags"].split(","))


def test_meta_full_tenant_and_operation() -> None:
    m = litellm_meta("sql_generation", tenant="stc-kuwait")
    assert m["user"] == "stc-kuwait"  # end_user defaults to tenant
    assert _tag_set(m) == {"app:aria", "tenant:stc-kuwait", "operation:sql_generation"}


def test_meta_explicit_user_overrides_tenant() -> None:
    m = litellm_meta("insight", tenant="acme", user="user-123")
    assert m["user"] == "user-123"
    assert "tenant:acme" in _tag_set(m)


def test_meta_without_tenant_still_tags_app_and_operation() -> None:
    # chart path has no tenant threaded → still attributable by app + operation.
    m = litellm_meta("chart")
    assert m["extra_headers"]["x-litellm-tags"] == "app:aria,operation:chart"
    assert m["user"] == "aria"


def test_tags_header_string() -> None:
    assert litellm_tags("insight", "acme") == "app:aria,operation:insight,tenant:acme"
