"""add_portfolio_holdings_refactor

Revision ID: bf42e088c42f
Revises: 9704b3110231
Create Date: 2026-05-31 20:52:35.619199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf42e088c42f'
down_revision: Union[str, Sequence[str], None] = '9704b3110231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add new columns to assets table
    op.add_column("assets", sa.Column("symbol", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("asset_type", sa.String(20), nullable=True, server_default="crypto"))
    op.add_column("assets", sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()))
    op.add_column("assets", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # 2. Add timestamps to portfolios
    op.add_column("portfolios", sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()))
    op.add_column("portfolios", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # 3. Create portfolio_holdings table
    op.create_table(
        "portfolio_holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("purchase_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("portfolio_id", "asset_id", name="uq_portfolio_holding"),
    )
    op.create_index("ix_holdings_portfolio_id", "portfolio_holdings", ["portfolio_id"])
    op.create_index("ix_holdings_asset_id", "portfolio_holdings", ["asset_id"])

    # 4. Migrate data: populate symbol from name
    op.execute("""
        UPDATE assets
        SET symbol = UPPER(REPLACE(REPLACE(name, ' ', ''), '.', ''))
        WHERE symbol IS NULL
    """)

    # 5. Create holdings from ALL assets (before deduplication removes them)
    op.execute("""
        INSERT INTO portfolio_holdings (portfolio_id, asset_id, quantity, created_at)
        SELECT a.portfolio_id, d.keep_id, 1.0, NOW()
        FROM assets a
        JOIN (
            SELECT name, MIN(id) as keep_id
            FROM assets
            GROUP BY name
        ) d ON a.name = d.name
        WHERE a.portfolio_id IS NOT NULL
    """)

    # 6. Deduplicate assets by name, keeping lowest ID
    op.execute("""
        WITH duplicates AS (
            SELECT name, MIN(id) as keep_id
            FROM assets
            GROUP BY name
        ),
        to_update AS (
            SELECT a.id as old_id, d.keep_id as new_id
            FROM assets a
            JOIN duplicates d ON a.name = d.name
            WHERE a.id != d.keep_id
        )
        UPDATE asset_prices
        SET asset_id = to_update.new_id
        FROM to_update
        WHERE asset_prices.asset_id = to_update.old_id
    """)

    op.execute("""
        WITH duplicates AS (
            SELECT name, MIN(id) as keep_id
            FROM assets
            GROUP BY name
        )
        DELETE FROM assets
        WHERE id NOT IN (SELECT keep_id FROM duplicates)
    """)

    # 7. Make symbol required and unique (after data migration)
    op.alter_column("assets", "symbol", nullable=False)
    op.create_unique_constraint("uq_asset_symbol", "assets", ["symbol"])
    op.create_index("ix_asset_symbol", "assets", ["symbol"])

    # 8. Change price column from Float to Numeric
    op.alter_column(
        "assets",
        "price",
        type_=sa.Numeric(18, 8),
        existing_type=sa.Float(),
        existing_nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse in opposite order
    op.alter_column("assets", "price", type_=sa.Float(), existing_type=sa.Numeric(18, 8))
    op.drop_index("ix_asset_symbol", "assets")
    op.drop_constraint("uq_asset_symbol", "assets")
    op.drop_index("ix_holdings_asset_id", "portfolio_holdings")
    op.drop_index("ix_holdings_portfolio_id", "portfolio_holdings")
    op.drop_table("portfolio_holdings")
    op.drop_column("portfolios", "updated_at")
    op.drop_column("portfolios", "created_at")
    op.drop_column("assets", "updated_at")
    op.drop_column("assets", "created_at")
    op.drop_column("assets", "asset_type")
    op.drop_column("assets", "symbol")
