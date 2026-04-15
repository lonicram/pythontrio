from sqlalchemy import Integer, String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)

    portfolio = relationship("Portfolio", back_populates="assets")
    prices = relationship("AssetPrice", back_populates="asset", cascade="all, delete-orphan")
