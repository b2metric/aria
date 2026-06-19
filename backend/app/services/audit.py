"""Audit service for recording and querying data-access events.

Every action that touches customer data (queries, exports, vault reads,
schema discoveries, etc.) should flow through this service to produce an
immutable audit trail in the ``data_audit_logs`` table.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.governance import DataAuditLog

logger = logging.getLogger(__name__)

# ── Well-known action constants ──────────────────────────────────────────


class AuditAction:
    """Canonical action names for ``DataAuditLog.action``."""

    QUERY = "query"
    EXPORT = "export"
    VIEW = "view"
    SCHEMA_DISCOVERY = "schema_discovery"
    VAULT_READ = "vault_read"
    VAULT_WRITE = "vault_write"
    DB_CONFIG_ACCESS = "db_config_access"
    POLICY_EVALUATION = "policy_evaluation"


class AuditResourceType:
    """Canonical resource-type names for ``DataAuditLog.resource_type``."""

    TABLE = "table"
    QUERY = "query"
    ARTIFACT = "artifact"
    VAULT_ENTRY = "vault_entry"
    DB_CONFIG = "db_config"
    POLICY = "policy"


# ── Service ──────────────────────────────────────────────────────────────


class AuditService:
    """Record and query data-access audit events.

    The service is intended to be used as a FastAPI dependency — inject an
    ``AsyncSession`` and instantiate per-request::

        async def my_endpoint(session: AsyncSession = Depends(get_session)):
            audit = AuditService(session)
            await audit.log_query(...)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Core write ──────────────────────────────────────────────────

    async def log_event(
        self,
        *,
        customer_id: uuid.UUID,
        action: str,
        resource_type: str,
        user_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> DataAuditLog:
        """Persist a single audit-log entry.

        Returns the newly created ``DataAuditLog`` instance (already flushed,
        so ``.id`` is populated).
        """
        entry = DataAuditLog(
            customer_id=customer_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        self._session.add(entry)
        await self._session.commit()
        logger.debug(
            "Audit: %s %s/%s user=%s customer=%s",
            action,
            resource_type,
            resource_id or "-",
            user_id,
            customer_id,
        )
        return entry

    # ── Convenience writers ─────────────────────────────────────────

    async def log_query(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        sql: str | None = None,
        row_count: int | None = None,
        question: str | None = None,
        explanation: str | None = None,
        ip_address: str | None = None,
    ) -> DataAuditLog:
        """Record a data-query event."""
        details: dict[str, Any] = {}
        if sql is not None:
            details["sql"] = sql
        if row_count is not None:
            details["row_count"] = row_count
        if question is not None:
            details["question"] = question
        if explanation is not None:
            details["explanation"] = explanation
        return await self.log_event(
            customer_id=customer_id,
            user_id=user_id,
            action=AuditAction.QUERY,
            resource_type=AuditResourceType.QUERY,
            resource_id=resource_id,
            details=details or None,
            ip_address=ip_address,
        )

    async def log_export(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        format: str | None = None,
        row_count: int | None = None,
        ip_address: str | None = None,
    ) -> DataAuditLog:
        """Record a data-export event."""
        details: dict[str, Any] = {}
        if format is not None:
            details["format"] = format
        if row_count is not None:
            details["row_count"] = row_count
        return await self.log_event(
            customer_id=customer_id,
            user_id=user_id,
            action=AuditAction.EXPORT,
            resource_type=AuditResourceType.ARTIFACT,
            resource_id=resource_id,
            details=details or None,
            ip_address=ip_address,
        )

    async def log_vault_read(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        table_name: str | None = None,
        ip_address: str | None = None,
    ) -> DataAuditLog:
        """Record a vault-knowledge read event."""
        details: dict[str, Any] = {}
        if table_name is not None:
            details["table_name"] = table_name
        return await self.log_event(
            customer_id=customer_id,
            user_id=user_id,
            action=AuditAction.VAULT_READ,
            resource_type=AuditResourceType.VAULT_ENTRY,
            resource_id=resource_id,
            details=details or None,
            ip_address=ip_address,
        )

    async def log_schema_discovery(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        db_config_id: str | None = None,
        table_count: int | None = None,
        ip_address: str | None = None,
    ) -> DataAuditLog:
        """Record a schema-discovery event."""
        details: dict[str, Any] = {}
        if db_config_id is not None:
            details["db_config_id"] = db_config_id
        if table_count is not None:
            details["table_count"] = table_count
        return await self.log_event(
            customer_id=customer_id,
            user_id=user_id,
            action=AuditAction.SCHEMA_DISCOVERY,
            resource_type=AuditResourceType.DB_CONFIG,
            resource_id=db_config_id,
            details=details or None,
            ip_address=ip_address,
        )

    async def log_policy_evaluation(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        policy_id: str | None = None,
        allowed: bool = True,
        ip_address: str | None = None,
    ) -> DataAuditLog:
        """Record a policy-evaluation event (RLS allow/deny)."""
        return await self.log_event(
            customer_id=customer_id,
            user_id=user_id,
            action=AuditAction.POLICY_EVALUATION,
            resource_type=AuditResourceType.POLICY,
            resource_id=policy_id,
            details={"allowed": allowed},
            ip_address=ip_address,
        )

    # ── Read / query ────────────────────────────────────────────────

    async def get_logs(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DataAuditLog]:
        """Return audit-log entries matching the given filters, newest first."""
        stmt = select(DataAuditLog).where(DataAuditLog.customer_id == customer_id)

        if user_id is not None:
            stmt = stmt.where(DataAuditLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(DataAuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(DataAuditLog.resource_type == resource_type)

        stmt = stmt.order_by(DataAuditLog.created_at.desc()).offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_logs(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> int:
        """Return the total number of matching audit-log entries."""
        stmt = (
            select(func.count())
            .select_from(DataAuditLog)
            .where(DataAuditLog.customer_id == customer_id)
        )

        if user_id is not None:
            stmt = stmt.where(DataAuditLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(DataAuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(DataAuditLog.resource_type == resource_type)

        result = await self._session.execute(stmt)
        return result.scalar_one()
