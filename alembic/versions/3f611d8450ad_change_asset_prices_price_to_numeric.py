"""change_asset_prices_price_to_numeric

Revision ID: 3f611d8450ad
Revises: 1600d4c6abb4
Create Date: 2026-05-31 21:12:20.284820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f611d8450ad'
down_revision: Union[str, Sequence[str], None] = '1600d4c6abb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "asset_prices",
        "price",
        type_=sa.Numeric(18, 8),
        existing_type=sa.Float(),
        existing_nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "asset_prices",
        "price",
        type_=sa.Float(),
        existing_type=sa.Numeric(18, 8),
        existing_nullable=False
    )
