"""Asset price history model."""

from sqlalchemy import (
    DECIMAL,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class AssetPriceHistory(Base):
    """Stores historical price records for assets.

    Each record represents a price snapshot at a specific point in time.
    Used for tracking price changes and generating price charts.
    """

    __tablename__ = "asset_price_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    price = Column(DECIMAL(precision=12, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    source = Column(String(50), nullable=True)  # e.g., 'yahoo', 'manual', 'cron'
    recorded_at = Column(DateTime, nullable=False)  # When the price was valid
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="price_history")

    # Composite index for efficient chart queries: get prices for an asset ordered by time
    __table_args__ = (
        Index(
            "ix_asset_price_history_asset_recorded",
            "asset_id",
            recorded_at.desc(),
        ),
    )
