"""add_user_profile_model_and_portfolio_owner

Revision ID: a1b2c3d4e5f6
Revises: 3f611d8450ad
Create Date: 2026-06-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3f611d8450ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_profiles table and owner_id to portfolios."""
    # 1. Create user_profiles table
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=True),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"], unique=True)
    op.create_index("ix_user_profiles_username", "user_profiles", ["username"], unique=True)

    # 2. Add owner_id to portfolios (nullable to preserve existing data)
    op.add_column(
        "portfolios",
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=True
        )
    )
    op.create_index("ix_portfolios_owner_id", "portfolios", ["owner_id"])


def downgrade() -> None:
    """Remove user_profiles table and owner_id from portfolios."""
    op.drop_index("ix_portfolios_owner_id", "portfolios")
    op.drop_column("portfolios", "owner_id")
    op.drop_index("ix_user_profiles_username", "user_profiles")
    op.drop_index("ix_user_profiles_email", "user_profiles")
    op.drop_table("user_profiles")