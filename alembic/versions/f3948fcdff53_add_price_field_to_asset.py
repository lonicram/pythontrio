"""Add price field to Asset

Revision ID: f3948fcdff53
Revises: 0f63f64b8d3e
Create Date: 2026-03-27 13:39:58.507910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3948fcdff53'
down_revision: Union[str, Sequence[str], None] = '0f63f64b8d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('assets', sa.Column('price', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assets', 'price')
