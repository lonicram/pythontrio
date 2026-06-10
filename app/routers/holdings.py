"""Portfolio holdings router for managing asset holdings within portfolios."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.schemas import HoldingResponse

router = APIRouter(prefix="/portfolios", tags=["holdings"])


class HoldingCreate(BaseModel):
    """Schema for adding a holding to a portfolio."""

    asset_id: int
    quantity: Decimal
    purchase_price: Decimal | None = None
    purchased_at: datetime | None = None


class HoldingUpdate(BaseModel):
    """Schema for updating a holding."""

    quantity: Decimal | None = None
    purchase_price: Decimal | None = None
    purchased_at: datetime | None = None


class AssetInfo(BaseModel):
    """Nested asset info in holding response."""

    id: int
    symbol: str
    name: str
    price: Decimal | None

    model_config = {"from_attributes": True}


class HoldingWithAssetResponse(HoldingResponse):
    """Holding response with nested asset details for this router."""

    portfolio_id: int
    purchased_at: datetime | None
    asset: AssetInfo


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingWithAssetResponse])
def list_holdings(
    portfolio_id: int, db: Session = Depends(get_db)
) -> list[PortfolioHolding]:
    """List all holdings in a portfolio."""
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .options(joinedload(PortfolioHolding.asset))
        .all()
    )
    return holdings


@router.post(
    "/{portfolio_id}/holdings", response_model=HoldingWithAssetResponse, status_code=201
)
def add_holding(
    portfolio_id: int, data: HoldingCreate, db: Session = Depends(get_db)
) -> PortfolioHolding:
    """Add an asset to a portfolio."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    asset = db.query(Asset).filter(Asset.id == data.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    existing = (
        db.query(PortfolioHolding)
        .filter(
            PortfolioHolding.portfolio_id == portfolio_id,
            PortfolioHolding.asset_id == data.asset_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Asset already in portfolio")

    holding = PortfolioHolding(portfolio_id=portfolio_id, **data.model_dump())
    db.add(holding)
    db.commit()

    result = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.id == holding.id)
        .options(joinedload(PortfolioHolding.asset))
        .first()
    )
    assert result is not None
    return result


@router.put(
    "/{portfolio_id}/holdings/{asset_id}", response_model=HoldingWithAssetResponse
)
def update_holding(
    portfolio_id: int,
    asset_id: int,
    data: HoldingUpdate,
    db: Session = Depends(get_db),
) -> PortfolioHolding:
    """Update a holding's quantity or purchase details."""
    holding = (
        db.query(PortfolioHolding)
        .filter(
            PortfolioHolding.portfolio_id == portfolio_id,
            PortfolioHolding.asset_id == asset_id,
        )
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(holding, key, value)

    db.commit()

    result = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.id == holding.id)
        .options(joinedload(PortfolioHolding.asset))
        .first()
    )
    assert result is not None
    return result


@router.delete("/{portfolio_id}/holdings/{asset_id}", status_code=204)
def remove_holding(
    portfolio_id: int, asset_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove an asset from a portfolio."""
    holding = (
        db.query(PortfolioHolding)
        .filter(
            PortfolioHolding.portfolio_id == portfolio_id,
            PortfolioHolding.asset_id == asset_id,
        )
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    db.delete(holding)
    db.commit()