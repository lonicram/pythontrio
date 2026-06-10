"""Asset price history endpoints for time-series data."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.asset import Asset
from app.models.asset_price import AssetPrice

router = APIRouter(prefix="/assets", tags=["asset-prices"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class AssetPriceCreate(BaseModel):
    """Schema for creating a single asset price record."""

    asset_id: int = Field(..., description="ID of the asset")
    price: float = Field(..., gt=0, description="Price value (must be positive)")
    recorded_at: datetime = Field(..., description="Timestamp when price was recorded")
    source: str | None = Field(None, max_length=100, description="Source of the price data")


class AssetPriceResponse(BaseModel):
    """Schema for a single asset price record response."""

    id: int
    asset_id: int
    price: float
    recorded_at: datetime
    source: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetPriceChartResponse(BaseModel):
    """Schema optimized for chart rendering with metadata."""

    asset_id: int
    asset_name: str
    prices: list[AssetPriceResponse]
    count: int
    from_date: datetime | None = None
    to_date: datetime | None = None


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/{asset_id}/prices", response_model=AssetPriceResponse, status_code=201)
def create_asset_price(
    asset_id: int,
    data: AssetPriceCreate,
    db: Session = Depends(get_db),
) -> AssetPrice:
    """Insert a single price record for an asset.

    This endpoint is primarily used by cronjobs to record new price snapshots.
    The price follows an append-only pattern and is never updated.

    Args:
        asset_id: The ID of the asset to record the price for.
        data: The price data to insert.
        db: Database session dependency.

    Returns:
        The newly created price record.

    Raises:
        HTTPException: 404 if asset not found, 400 if asset_id mismatch.
    """
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Ensure asset_id in path matches asset_id in body
    if data.asset_id != asset_id:
        raise HTTPException(
            status_code=400,
            detail=f"Asset ID mismatch: path={asset_id}, body={data.asset_id}",
        )

    # Create price record
    asset_price = AssetPrice(**data.model_dump())
    db.add(asset_price)

    # Optional: Update asset's current price for denormalization (fast reads)
    asset.price = Decimal(str(data.price))

    db.commit()
    db.refresh(asset_price)

    return asset_price


@router.get("/{asset_id}/prices", response_model=AssetPriceChartResponse)
def get_asset_price_history(
    asset_id: int,
    from_date: datetime | None = Query(None, description="Start date for price range"),
    to_date: datetime | None = Query(None, description="End date for price range"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
) -> AssetPriceChartResponse:
    """Get historical price data for an asset with optional time-range filtering.

    This endpoint is used by frontends to render price charts. Results are
    ordered by recorded_at descending (newest first) and support pagination.

    Args:
        asset_id: The ID of the asset.
        from_date: Optional start date filter (inclusive).
        to_date: Optional end date filter (inclusive).
        limit: Maximum number of records to return (1-10000).
        offset: Number of records to skip for pagination.
        db: Database session dependency.

    Returns:
        Chart-optimized response with price history and metadata.

    Raises:
        HTTPException: 404 if asset not found.
    """
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Build query with filters
    query = db.query(AssetPrice).filter(AssetPrice.asset_id == asset_id)

    if from_date:
        query = query.filter(AssetPrice.recorded_at >= from_date)
    if to_date:
        query = query.filter(AssetPrice.recorded_at <= to_date)

    # Get total count for metadata
    total_count = query.count()

    # Apply ordering and pagination
    prices = (
        query.order_by(desc(AssetPrice.recorded_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    return AssetPriceChartResponse(
        asset_id=asset.id,
        asset_name=asset.name,
        prices=[AssetPriceResponse.model_validate(p) for p in prices],
        count=total_count,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/{asset_id}/prices/latest", response_model=AssetPriceResponse)
def get_latest_asset_price(
    asset_id: int,
    db: Session = Depends(get_db),
) -> AssetPrice:
    """Get the most recent price record for an asset.

    Args:
        asset_id: The ID of the asset.
        db: Database session dependency.

    Returns:
        The most recent price record.

    Raises:
        HTTPException: 404 if asset or price not found.
    """
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get latest price
    latest_price = (
        db.query(AssetPrice)
        .filter(AssetPrice.asset_id == asset_id)
        .order_by(desc(AssetPrice.recorded_at))
        .first()
    )

    if not latest_price:
        raise HTTPException(
            status_code=404,
            detail=f"No price history found for asset {asset_id}",
        )

    return latest_price