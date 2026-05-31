"""remove_asset_portfolio_fk

Revision ID: 1600d4c6abb4
Revises: bf42e088c42f
Create Date: 2026-05-31 20:54:25.564467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1600d4c6abb4'
down_revision: Union[str, Sequence[str], None] = 'bf42e088c42f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove old foreign key and column
    op.drop_constraint("assets_portfolio_id_fkey", "assets", type_="foreignkey")
    op.drop_column("assets", "portfolio_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("assets", sa.Column("portfolio_id", sa.Integer(), nullable=True))
    # Restore portfolio_id from holdings (note: loses multi-portfolio relationships)
    op.execute("""
        UPDATE assets a
        SET portfolio_id = (
            SELECT portfolio_id FROM portfolio_holdings ph
            WHERE ph.asset_id = a.id LIMIT 1
        )
    """)
    op.create_foreign_key("assets_portfolio_id_fkey", "assets", "portfolios", ["portfolio_id"], ["id"])
