"""Schemas for Asset model."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AssetBase(BaseModel):
    """Base schema for Asset with common attributes."""

    name: str
    code: str
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
    model_config = ConfigDict(from_attributes=True)
