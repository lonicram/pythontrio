"""Add ON DELETE CASCADE to asset_price_history foreign key

Revision ID: 27af1138d7cb
Revises: 5667813b8c40
Create Date: 2026-03-19 20:09:25.534360

"""
from collections.abc import Sequence

from alembic import op
from app.migration_utils import is_sqlite

# revision identifiers, used by Alembic.
revision: str = "27af1138d7cb"
down_revision: str | Sequence[str] | None = "5667813b8c40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to asset_price_history.asset_id foreign key."""
    # SQLite creates this FK with CASCADE in 5667813b8c40; altering FKs is not portable.
    if is_sqlite():
        return

    op.drop_constraint(
        op.f("asset_price_history_asset_id_fkey"),
        "asset_price_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("asset_price_history_asset_id_fkey"),
        "asset_price_history",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Remove ON DELETE CASCADE from asset_price_history.asset_id foreign key."""
    if is_sqlite():
        return

    op.drop_constraint(
        op.f("asset_price_history_asset_id_fkey"),
        "asset_price_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("asset_price_history_asset_id_fkey"),
        "asset_price_history",
        "assets",
        ["asset_id"],
        ["id"],
    )
