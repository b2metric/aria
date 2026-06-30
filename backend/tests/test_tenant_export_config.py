"""Phase 1 — two-threshold export config (DBConfig DTO + admin API + invariant)."""

from __future__ import annotations

import pytest

from backend.app.db.models import DBConfig, DatabaseType


def test_dbconfig_has_export_fields_with_defaults():
    cfg = DBConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="h",
        port=5432,
        database="d",
        username="u",
        password="p",
    )
    # display ceiling unchanged
    assert cfg.max_row_limit == 1000
    # new export ceiling + batch size defaults
    assert cfg.max_export_row_limit == 100_000
    assert cfg.export_batch_size == 50_000


# ---------------------------------------------------------------------------
# Task 4 — TenantConfigUpdate request/response model tests
# ---------------------------------------------------------------------------

from pydantic import ValidationError

from backend.app.api.endpoints.admin.tenant import TenantConfigUpdate


def test_update_accepts_new_fields():
    body = TenantConfigUpdate(
        max_row_limit=1000, max_export_row_limit=200_000, export_batch_size=20_000
    )
    assert body.max_row_limit == 1000
    assert body.max_export_row_limit == 200_000
    assert body.export_batch_size == 20_000


def test_update_rejects_export_below_query_when_both_present():
    with pytest.raises(ValidationError):
        TenantConfigUpdate(max_row_limit=50_000, max_export_row_limit=10_000)


def test_update_rejects_batch_above_export_when_both_present():
    with pytest.raises(ValidationError):
        TenantConfigUpdate(max_export_row_limit=10_000, export_batch_size=20_000)


def test_update_allows_partial_single_field():
    # only one of the related fields → no cross-field error at request level
    body = TenantConfigUpdate(export_batch_size=5_000)
    assert body.export_batch_size == 5_000


def test_query_limit_has_no_lower_floor():
    # the previous ge=100 floor is removed
    body = TenantConfigUpdate(max_row_limit=1)
    assert body.max_row_limit == 1


# ---------------------------------------------------------------------------
# Task 6 — validate_row_limit_invariant helper tests
# ---------------------------------------------------------------------------

from backend.app.api.endpoints.admin.tenant import validate_row_limit_invariant


def test_invariant_helper_accepts_valid_combo():
    # display ≤ export ≤ 1M and batch ≤ export
    validate_row_limit_invariant(max_row=1000, max_export=100_000, batch=50_000)  # no raise


def test_invariant_helper_rejects_export_below_display():
    with pytest.raises(ValueError):
        validate_row_limit_invariant(max_row=200_000, max_export=100_000, batch=50_000)


def test_invariant_helper_rejects_batch_above_export():
    with pytest.raises(ValueError):
        validate_row_limit_invariant(max_row=1000, max_export=100_000, batch=200_000)


def test_invariant_helper_rejects_above_hard_ceiling():
    with pytest.raises(ValueError):
        validate_row_limit_invariant(max_row=1000, max_export=2_000_000, batch=50_000)


def test_invariant_helper_accepts_equality_boundaries():
    # max_row == max_export == ceiling and batch == max_export are all valid
    from backend.app.api.endpoints.admin.tenant import HARD_ROW_CEILING

    validate_row_limit_invariant(
        max_row=HARD_ROW_CEILING,
        max_export=HARD_ROW_CEILING,
        batch=HARD_ROW_CEILING,
    )  # no raise
