from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class StarterHolding(BaseModel):
    """A holding to add to the starter portfolio."""
    asset_id: int
    quantity: Decimal = Field(..., gt=0)
    purchase_price: Decimal | None = None


class UserOnboardRequest(BaseModel):
    """Request for user onboarding with starter portfolio."""
    email: EmailStr
    username: str | None = Field(None, max_length=50)
    full_name: str | None = Field(None, max_length=100)
    portfolio_name: str = Field(default="My Portfolio", max_length=100)
    portfolio_description: str | None = Field(None, max_length=500)
    starter_holdings: list[StarterHolding] = Field(default_factory=list, max_length=20)


class HoldingOut(BaseModel):
    """Response schema for a portfolio holding."""
    asset_id: int
    quantity: Decimal
    purchase_price: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    """Response schema for a portfolio."""
    id: int
    name: str
    description: str | None
    holdings: list[HoldingOut]

    model_config = {"from_attributes": True}


class UserOnboardResponse(BaseModel):
    """Response for successful user onboarding."""
    id: int
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    portfolios: list[PortfolioOut]

    model_config = {"from_attributes": True}