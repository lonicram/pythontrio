"""Shared helpers for dialect-aware Alembic migrations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


def is_sqlite() -> bool:
    """Return True when the migration bind uses SQLite."""
    return op.get_bind().dialect.name == "sqlite"


def datetime_server_default() -> sa.TextClause:
    """Return a dialect-appropriate server default for timestamp columns."""
    if is_sqlite():
        return sa.text("(CURRENT_TIMESTAMP)")
    return sa.text("now()")
