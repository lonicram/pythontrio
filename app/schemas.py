"""Pydantic schemas for API request/response validation."""

from decimal import Decimal

from pydantic import BaseModel


class AssetBase(BaseModel):
    """Base schema for Asset with common attributes."""

    name: str
    description: str | None = None
    type: str
    price: Decimal | None = None
    portfolio_id: int


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""

    pass


class AssetResponse(AssetBase):
    """Schema for asset response with database fields."""

    id: int

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True
