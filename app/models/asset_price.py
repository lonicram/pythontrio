"""AssetPrice model for storing historical asset price data."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetPrice(Base):
    """Time-series table for historical asset prices.

    This table follows an append-only pattern where prices are never updated,
    only inserted. This simplifies concurrency and enables efficient bulk writes.
    """

    __tablename__ = "asset_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), server_default=func.now()
    )

    # Relationship to Asset
    asset = relationship("Asset", back_populates="prices")

    # Composite index for efficient time-range queries
    __table_args__ = (
        Index("ix_asset_prices_asset_id_recorded_at", "asset_id", "recorded_at"),
    )