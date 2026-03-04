"""Asset model."""

from sqlalchemy import DECIMAL, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Asset(Base):
    """Example asset model for demonstration."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    type = Column(String(100), nullable=False)
    price = Column(DECIMAL(precision=12, scale=2), nullable=True)

    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)

    portfolio = relationship("Portfolio", back_populates="assets")
