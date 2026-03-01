"""SQLAlchemy ORM models.

Import all models here so they are registered with SQLAlchemy's metadata.
This allows Alembic to discover all models with a single import:

    from app.models import Base, Asset, Portfolio
"""

from app.models.asset import Asset
from app.models.portfolio import Portfolio

__all__ = ["Asset", "Portfolio"]
