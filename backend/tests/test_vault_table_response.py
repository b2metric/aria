"""Regression: GET /vault/tables/{name} 500'd (→ browser "Failed to fetch") because
YAML parses a bare ISO ``generated_at:`` timestamp as a datetime, and
VaultTableResponse.generated_at is ``str | None`` → pydantic string_type error.

_parse_vault_file_for_api must coerce generated_at/enriched_at to strings.
"""

from __future__ import annotations

from backend.app.api.workspaces import VaultTableResponse, _parse_vault_file_for_api

_MD = """---
table: FCT_X
database: oracle
workspace: stc-kuwait
keywords: [a, b]
description: "A table"
generated_at: 2026-07-01T22:24:18.299165+00:00
---

# FCT_X

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| A | NUMBER | ✓ |  | col a |
"""


def test_generated_at_bare_timestamp_is_coerced_and_response_builds(tmp_path):
    f = tmp_path / "fct_x.md"
    f.write_text(_MD, encoding="utf-8")

    data = _parse_vault_file_for_api(f)
    # YAML turns a bare ISO timestamp into a datetime — the API layer must stringify it.
    assert isinstance(data["generated_at"], str)

    # The response model (generated_at: str | None) must build without a ValidationError.
    resp = VaultTableResponse(**data)
    assert resp.generated_at is not None and resp.generated_at.startswith("2026-07-01")
    assert resp.table_name == "FCT_X"
