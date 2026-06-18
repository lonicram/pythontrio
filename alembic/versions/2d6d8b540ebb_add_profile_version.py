"""add profile version

Revision ID: 2d6d8b540ebb
Revises: c00d7ae13f11
Create Date: 2026-06-18 16:59:34.273406

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d6d8b540ebb"
down_revision: Union[str, Sequence[str], None] = "c00d7ae13f11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_profiles",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_profiles", "version")
