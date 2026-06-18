"""add_profile_status

Revision ID: c00d7ae13f11
Revises: a1b2c3d4e5f6
Create Date: 2026-06-18 14:35:05.451680

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c00d7ae13f11"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    profile_status = sa.Enum(
        "new", "verified", "suspended", "deleted", name="profile_status"
    )
    profile_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "user_profiles",
        sa.Column("status", profile_status, nullable=False, server_default="new"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_profiles", "status")
    sa.Enum(name="profile_status").drop(op.get_bind(), checkfirst=True)
