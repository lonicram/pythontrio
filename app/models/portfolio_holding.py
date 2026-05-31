"""PortfolioHolding model - junction table for Portfolio-Asset relationship."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.portfolio import Portfolio


class PortfolioHolding(Base):
    """Represents an asset holding within a portfolio.

    This junction table enables many-to-many relationship between
    portfolios and assets, with additional metadata like quantity
    and purchase price for P&L calculations.
    """

    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),  # Don't delete assets with holdings
        nullable=False
    )

    # Holding details
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        default=Decimal("0")
    )
    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Price per unit when acquired"
    )
    purchased_at: Mapped[datetime | None] = mapped_column(nullable=True)

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
    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship(back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", name="uq_portfolio_holding"),
        Index("ix_holdings_portfolio_id", "portfolio_id"),
        Index("ix_holdings_asset_id", "asset_id"),
    )

    def __repr__(self) -> str:
        return f"<PortfolioHolding(portfolio={self.portfolio_id}, asset={self.asset_id}, qty={self.quantity})>"