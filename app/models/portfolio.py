"""Portfolio model with holdings relationship."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.portfolio_holding import PortfolioHolding
    from app.models.user_profile import UserProfile


class Portfolio(Base):
    """User portfolio containing asset holdings."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional user profile who owns this portfolio"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
    owner: Mapped["UserProfile | None"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan"
    )

    @property
    def total_value(self) -> Decimal:
        """Calculate total portfolio value from holdings."""
        return sum(
            (
                (h.quantity * h.asset.price)
                for h in self.holdings
                if h.asset.price is not None
            ),
            Decimal("0"),
        )

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name={self.name})>"