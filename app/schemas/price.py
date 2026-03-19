"""Schemas for Asset Price History model."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class AssetPriceHistoryBase(BaseModel):
    """Base schema for asset price history."""

    price: Decimal
    currency: str = "USD"
    source: str | None = None
    recorded_at: datetime

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        """Validate that price is a positive number.

        Args:
            v: The price value to validate.

        Returns:
            The validated price.

        Raises:
            ValueError: If price is not positive.
        """
        if v <= 0:
            raise ValueError("price must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def currency_must_be_valid(cls, v: str) -> str:
        """Validate currency code format.

        Args:
            v: The currency code to validate.

        Returns:
            The validated currency code in uppercase.

        Raises:
            ValueError: If currency is not 1-3 characters.
        """
        v = v.upper().strip()
        if not v or len(v) > 3:
            raise ValueError("currency must be 1-3 characters")
        return v


class AssetPriceHistoryCreate(AssetPriceHistoryBase):
    """Schema for recording a new price."""

    asset_id: int


class AssetPriceHistoryResponse(AssetPriceHistoryBase):
    """Schema for price history response."""

    id: int
    asset_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssetPriceChartPoint(BaseModel):
    """Simplified schema for chart data points."""

    price: Decimal
    recorded_at: datetime


class AssetPriceChartResponse(BaseModel):
    """Schema for chart data response."""

    asset_id: int
    asset_name: str
    currency: str
    data_points: list[AssetPriceChartPoint]
