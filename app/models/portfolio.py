"""Portfolio model."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Portfolio(Base):
    """Example portfolio model for demonstration."""

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    assets = relationship("Asset", back_populates="portfolio")
