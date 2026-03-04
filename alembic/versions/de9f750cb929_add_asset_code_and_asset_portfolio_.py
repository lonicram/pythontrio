"""Add Asset.code and Asset|Portfolio.created_at

Revision ID: de9f750cb929
Revises: f3b2fac2a421
Create Date: 2026-03-04 22:09:13.275969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de9f750cb929'
down_revision: Union[str, Sequence[str], None] = 'f3b2fac2a421'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add code column as nullable first, then backfill and make NOT NULL
    op.add_column('assets', sa.Column('code', sa.String(length=100), nullable=True))
    op.execute("UPDATE assets SET code = 'UNKNOWN' WHERE code IS NULL")
    op.alter_column('assets', 'code', nullable=False)

    op.add_column('assets', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.add_column('portfolios', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('portfolios', 'created_at')
    op.drop_column('assets', 'created_at')
    op.drop_column('assets', 'code')
