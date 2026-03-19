"""Pydantic schemas for API request/response validation.

This module re-exports all schemas from submodules for backward compatibility.
"""

from app.schemas.asset import AssetBase, AssetCreate, AssetResponse
from app.schemas.portfolio import PortfolioBase, PortfolioCreate, PortfolioResponse
from app.schemas.price import (
    AssetPriceChartPoint,
    AssetPriceChartResponse,
    AssetPriceHistoryBase,
    AssetPriceHistoryCreate,
    AssetPriceHistoryResponse,
)

__all__ = [
    # Asset schemas
    "AssetBase",
    "AssetCreate",
    "AssetResponse",
    # Portfolio schemas
    "PortfolioBase",
    "PortfolioCreate",
    "PortfolioResponse",
    # Price history schemas
    "AssetPriceHistoryBase",
    "AssetPriceHistoryCreate",
    "AssetPriceHistoryResponse",
    "AssetPriceChartPoint",
    "AssetPriceChartResponse",
]
