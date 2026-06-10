"""Shared Pydantic response schemas for REST API and MCP tools."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AssetResponse(BaseModel):
    """Asset response schema."""

    id: int
    symbol: str
    name: str
    asset_type: str
    description: str | None
    price: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    """Portfolio response schema."""

    id: int
    owner_id: int | None
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class HoldingResponse(BaseModel):
    """Portfolio holding response schema."""

    id: int
    asset_id: int
    quantity: Decimal
    purchase_price: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioWithHoldingsResponse(BaseModel):
    """Portfolio with nested holdings."""

    id: int
    owner_id: int | None
    name: str
    description: str | None
    holdings: list[HoldingResponse]

    model_config = {"from_attributes": True}


class UserProfileResponse(BaseModel):
    """User profile response schema."""

    id: int
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}