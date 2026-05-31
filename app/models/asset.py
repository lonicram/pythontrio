"""Asset model - master catalog of tradeable assets."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.asset_price import AssetPrice
    from app.models.portfolio_holding import PortfolioHolding


class Asset(Base):
    """Master asset definition (e.g., Bitcoin, AAPL).

    Each asset exists once in the system with a single current price.
    Portfolios reference assets through PortfolioHolding.
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique ticker symbol (BTC, AAPL)"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name (Bitcoin, Apple Inc.)"
    )
    asset_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="crypto",
        comment="Asset category: crypto, stock, etf, commodity"
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Current market price (single source of truth)"
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        back_populates="asset"
    )
    prices: Mapped[list["AssetPrice"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(symbol={self.symbol}, name={self.name}, price={self.price})>"