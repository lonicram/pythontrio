"""Add ON DELETE CASCADE to asset_price_history foreign key

Revision ID: 27af1138d7cb
Revises: 5667813b8c40
Create Date: 2026-03-19 20:09:25.534360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27af1138d7cb'
down_revision: Union[str, Sequence[str], None] = '5667813b8c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add ON DELETE CASCADE to asset_price_history.asset_id foreign key."""
    op.drop_constraint(
        op.f('asset_price_history_asset_id_fkey'),
        'asset_price_history',
        type_='foreignkey'
    )
    op.create_foreign_key(
        op.f('asset_price_history_asset_id_fkey'),
        'asset_price_history',
        'assets',
        ['asset_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema: Remove ON DELETE CASCADE from asset_price_history.asset_id foreign key."""
    op.drop_constraint(
        op.f('asset_price_history_asset_id_fkey'),
        'asset_price_history',
        type_='foreignkey'
    )
    op.create_foreign_key(
        op.f('asset_price_history_asset_id_fkey'),
        'asset_price_history',
        'assets',
        ['asset_id'],
        ['id']
    )
