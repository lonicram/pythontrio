"""Schemas for Portfolio model."""

from pydantic import BaseModel, ConfigDict


class PortfolioBase(BaseModel):
    """Base schema for Portfolio with common attributes."""

    name: str
    description: str | None = None


class PortfolioCreate(PortfolioBase):
    """Schema for creating a new portfolio."""

    pass


class PortfolioResponse(PortfolioBase):
    """Schema for portfolio response with database fields."""

    id: int
    model_config = ConfigDict(from_attributes=True)
