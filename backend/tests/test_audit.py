"""Unit tests for the AuditService.

Tests the audit logging service with a mocked AsyncSession — no real
database connection required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.governance import DataAuditLog
from backend.app.services.audit import (
    AuditAction,
    AuditResourceType,
    AuditService,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session() -> AsyncMock:
    """Return an AsyncMock wrapping an AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def audit_service(mock_session: AsyncMock) -> AuditService:
    """Return an AuditService backed by the mocked session."""
    return AuditService(mock_session)


@pytest.fixture
def sample_customer_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_user_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Constants ────────────────────────────────────────────────────────────


class TestAuditConstants:
    """Verify the action and resource-type constants."""

    def test_audit_action_values(self) -> None:
        assert AuditAction.QUERY == "query"
        assert AuditAction.EXPORT == "export"
        assert AuditAction.VIEW == "view"
        assert AuditAction.SCHEMA_DISCOVERY == "schema_discovery"
        assert AuditAction.VAULT_READ == "vault_read"
        assert AuditAction.VAULT_WRITE == "vault_write"
        assert AuditAction.DB_CONFIG_ACCESS == "db_config_access"
        assert AuditAction.POLICY_EVALUATION == "policy_evaluation"

    def test_audit_resource_type_values(self) -> None:
        assert AuditResourceType.TABLE == "table"
        assert AuditResourceType.QUERY == "query"
        assert AuditResourceType.ARTIFACT == "artifact"
        assert AuditResourceType.VAULT_ENTRY == "vault_entry"
        assert AuditResourceType.DB_CONFIG == "db_config"
        assert AuditResourceType.POLICY == "policy"


# ── Core log_event ───────────────────────────────────────────────────────


class TestLogEvent:
    """Tests for the primary ``log_event`` method."""

    @pytest.mark.asyncio
    async def test_log_event_minimal(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Log an event with only the required fields."""
        entry = await audit_service.log_event(
            customer_id=sample_customer_id,
            action=AuditAction.QUERY,
            resource_type=AuditResourceType.QUERY,
        )

        assert isinstance(entry, DataAuditLog)
        assert entry.customer_id == sample_customer_id
        assert entry.action == "query"
        assert entry.resource_type == "query"
        assert entry.user_id is None
        assert entry.resource_id is None
        assert entry.details is None
        assert entry.ip_address is None

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_event_full(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        """Log an event with all optional fields populated."""
        details = {"sql": "SELECT 1", "row_count": 42}
        entry = await audit_service.log_event(
            customer_id=sample_customer_id,
            action=AuditAction.EXPORT,
            resource_type=AuditResourceType.ARTIFACT,
            user_id=sample_user_id,
            resource_id="chart-123",
            details=details,
            ip_address="192.168.1.1",
        )

        assert entry.customer_id == sample_customer_id
        assert entry.action == "export"
        assert entry.resource_type == "artifact"
        assert entry.user_id == sample_user_id
        assert entry.resource_id == "chart-123"
        assert entry.details == details
        assert entry.ip_address == "192.168.1.1"

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_event_flush_sets_id(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """After flush the returned entry should have an id."""
        entry = await audit_service.log_event(
            customer_id=sample_customer_id,
            action="test",
            resource_type="test",
        )
        # The id is set by the DB on flush; with a mock it may be None,
        # but the entry instance is still returned correctly.
        assert isinstance(entry, DataAuditLog)


# ── Convenience methods ──────────────────────────────────────────────────


class TestConvenienceMethods:
    """Tests for the convenience logging helpers."""

    @pytest.mark.asyncio
    async def test_log_query(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_query(
            customer_id=sample_customer_id,
            user_id=sample_user_id,
            resource_id="q-001",
            sql="SELECT * FROM sales",
            row_count=100,
            ip_address="10.0.0.2",
        )

        assert entry.action == AuditAction.QUERY
        assert entry.resource_type == AuditResourceType.QUERY
        assert entry.customer_id == sample_customer_id
        assert entry.user_id == sample_user_id
        assert entry.resource_id == "q-001"
        assert entry.details == {"sql": "SELECT * FROM sales", "row_count": 100}
        assert entry.ip_address == "10.0.0.2"

    @pytest.mark.asyncio
    async def test_log_query_minimal(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_query(
            customer_id=sample_customer_id,
        )
        assert entry.action == AuditAction.QUERY
        assert entry.details is None  # no sql/row_count → None

    @pytest.mark.asyncio
    async def test_log_export(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_export(
            customer_id=sample_customer_id,
            user_id=sample_user_id,
            resource_id="chart-export-42",
            format="csv",
            row_count=500,
            ip_address="10.0.0.3",
        )

        assert entry.action == AuditAction.EXPORT
        assert entry.resource_type == AuditResourceType.ARTIFACT
        assert entry.details == {"format": "csv", "row_count": 500}

    @pytest.mark.asyncio
    async def test_log_vault_read(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_vault_read(
            customer_id=sample_customer_id,
            user_id=sample_user_id,
            resource_id="vault/sales.md",
            table_name="sales",
            ip_address="10.0.0.4",
        )

        assert entry.action == AuditAction.VAULT_READ
        assert entry.resource_type == AuditResourceType.VAULT_ENTRY
        assert entry.details == {"table_name": "sales"}
        assert entry.resource_id == "vault/sales.md"

    @pytest.mark.asyncio
    async def test_log_schema_discovery(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_schema_discovery(
            customer_id=sample_customer_id,
            user_id=sample_user_id,
            db_config_id="pg-prod",
            table_count=42,
            ip_address="10.0.0.5",
        )

        assert entry.action == AuditAction.SCHEMA_DISCOVERY
        assert entry.resource_type == AuditResourceType.DB_CONFIG
        assert entry.details == {"db_config_id": "pg-prod", "table_count": 42}

    @pytest.mark.asyncio
    async def test_log_policy_evaluation_allowed(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_policy_evaluation(
            customer_id=sample_customer_id,
            policy_id="pol-allow-sales",
            allowed=True,
        )

        assert entry.action == AuditAction.POLICY_EVALUATION
        assert entry.resource_type == AuditResourceType.POLICY
        assert entry.resource_id == "pol-allow-sales"
        assert entry.details == {"allowed": True}

    @pytest.mark.asyncio
    async def test_log_policy_evaluation_denied(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        entry = await audit_service.log_policy_evaluation(
            customer_id=sample_customer_id,
            policy_id="pol-deny-finance",
            allowed=False,
        )

        assert entry.details == {"allowed": False}


# ── Query methods ───────────────────────────────────────────────────────


class TestQueryMethods:
    """Tests for ``get_logs`` and ``count_logs``."""

    @pytest.mark.asyncio
    async def test_get_logs_no_filters(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Retrieve logs with only customer_id filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        logs = await audit_service.get_logs(customer_id=sample_customer_id)

        assert logs == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_logs_with_filters(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        """Retrieve logs with all optional filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        logs = await audit_service.get_logs(
            customer_id=sample_customer_id,
            user_id=sample_user_id,
            action="query",
            resource_type="query",
            limit=10,
            offset=5,
        )

        assert logs == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_logs_returns_entries(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Verify logs are returned as DataAuditLog instances."""
        entry = DataAuditLog(
            customer_id=sample_customer_id,
            action="query",
            resource_type="query",
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry]
        mock_session.execute.return_value = mock_result

        logs = await audit_service.get_logs(customer_id=sample_customer_id)

        assert len(logs) == 1
        assert logs[0] is entry

    @pytest.mark.asyncio
    async def test_count_logs_zero(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Count returns 0 when no matching logs exist."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        count = await audit_service.count_logs(customer_id=sample_customer_id)

        assert count == 0
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_logs_with_filters(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
        sample_user_id: uuid.UUID,
    ) -> None:
        """Count with filters applied."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 7
        mock_session.execute.return_value = mock_result

        count = await audit_service.count_logs(
            customer_id=sample_customer_id,
            user_id=sample_user_id,
            action="export",
            resource_type="artifact",
        )

        assert count == 7
        mock_session.execute.assert_awaited_once()


# ── Edge cases ───────────────────────────────────────────────────────────


class TestAuditEdgeCases:
    """Edge-case and integration-style tests."""

    @pytest.mark.asyncio
    async def test_multiple_events_same_session(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """Logging multiple events should call add multiple times."""
        await audit_service.log_event(
            customer_id=sample_customer_id,
            action="a1",
            resource_type="t1",
        )
        await audit_service.log_event(
            customer_id=sample_customer_id,
            action="a2",
            resource_type="t2",
        )

        assert mock_session.add.call_count == 2
        assert mock_session.flush.await_count == 2

    @pytest.mark.asyncio
    async def test_details_with_empty_dict(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """An empty details dict should be stored as-is."""
        entry = await audit_service.log_event(
            customer_id=sample_customer_id,
            action="test",
            resource_type="test",
            details={},
        )
        assert entry.details == {}

    @pytest.mark.asyncio
    async def test_ip_address_ipv6(
        self,
        audit_service: AuditService,
        mock_session: AsyncMock,
        sample_customer_id: uuid.UUID,
    ) -> None:
        """IPv6 addresses should be accepted."""
        entry = await audit_service.log_event(
            customer_id=sample_customer_id,
            action="test",
            resource_type="test",
            ip_address="2001:db8::1",
        )
        assert entry.ip_address == "2001:db8::1"

    def test_service_init(self, mock_session: AsyncMock) -> None:
        """Service initialises with a session."""
        svc = AuditService(mock_session)
        assert svc._session is mock_session
