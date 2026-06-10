"""Pydantic schemas for request/response validation."""

from app.schemas.onboarding import (
    HoldingOut,
    PortfolioOut,
    StarterHolding,
    UserOnboardRequest,
    UserOnboardResponse,
)
from app.schemas.responses import (
    AssetResponse,
    HoldingResponse,
    PortfolioResponse,
    PortfolioWithHoldingsResponse,
    UserProfileResponse,
)

__all__ = [
    # Onboarding
    "HoldingOut",
    "PortfolioOut",
    "StarterHolding",
    "UserOnboardRequest",
    "UserOnboardResponse",
    # Responses (shared)
    "AssetResponse",
    "HoldingResponse",
    "PortfolioResponse",
    "PortfolioWithHoldingsResponse",
    "UserProfileResponse",
]