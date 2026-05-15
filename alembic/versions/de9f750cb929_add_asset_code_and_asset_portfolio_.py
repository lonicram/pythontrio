"""Add Asset.code and Asset|Portfolio.created_at

Revision ID: de9f750cb929
Revises: f3b2fac2a421
Create Date: 2026-03-04 22:09:13.275969

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.migration_utils import datetime_server_default

# revision identifiers, used by Alembic.
revision: str = "de9f750cb929"
down_revision: str | Sequence[str] | None = "f3b2fac2a421"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use NOT NULL + server_default so SQLite does not need ALTER COLUMN.
    op.add_column(
        "assets",
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
            server_default="UNKNOWN",
        ),
    )

    created_at_default = datetime_server_default()
    op.add_column(
        "assets",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=created_at_default,
            nullable=False,
        ),
    )
    op.add_column(
        "portfolios",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=created_at_default,
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("portfolios", "created_at")
    op.drop_column("assets", "created_at")
    op.drop_column("assets", "code")
