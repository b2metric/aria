"""ARIA database models.

Re-exports the declarative ``Base`` and imports every model module so that
``Base.metadata`` is fully populated. ``backend/alembic/env.py`` does
``from backend.app.models import Base`` and uses ``Base.metadata`` as the
autogenerate target, so the package must expose ``Base`` and register all tables.
"""

from backend.app.models.base import Base, TimestampMixin, UUIDMixin, utcnow

# Side-effect imports: register every table on ``Base.metadata``.
from . import (  # noqa: F401  (imported for metadata registration, not direct use)
    artifact,
    database,
    enums,
    governance,
    memory,
    organization,
    query,
    token,
)

__all__ = ["Base", "TimestampMixin", "UUIDMixin", "utcnow"]
import backend.app.models.database_events  # noqa: F401
