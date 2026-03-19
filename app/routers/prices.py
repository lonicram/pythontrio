"""Price history API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.exceptions import AssetNotFoundError
from app.models import Asset
from app.schemas import (
    AssetPriceChartPoint,
    AssetPriceChartResponse,
    AssetPriceHistoryCreate,
    AssetPriceHistoryResponse,
)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/", response_model=AssetPriceHistoryResponse, status_code=201)
def record_price(
    price_data: AssetPriceHistoryCreate, db: Session = Depends(get_db)
) -> AssetPriceHistoryResponse:
    """Record a new price for an asset.

    This endpoint is designed to be called by:
    - Manual price updates
    - Cron jobs fetching prices from external sources

    Args:
        price_data: Price data including asset_id, price, currency, source, recorded_at.
        db: Database session.

    Returns:
        The created price history record.

    Raises:
        HTTPException: 404 if asset not found.
    """
    try:
        record = crud.record_asset_price(
            db=db,
            asset_id=price_data.asset_id,
            price=price_data.price,
            recorded_at=price_data.recorded_at,
            currency=price_data.currency,
            source=price_data.source,
        )
        return record
    except AssetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/assets/{asset_id}/history", response_model=list[AssetPriceHistoryResponse]
)
def get_price_history(
    asset_id: int,
    start_date: datetime | None = Query(None, description="Filter from this date"),
    end_date: datetime | None = Query(None, description="Filter until this date"),
    limit: int = Query(100, le=1000, description="Max records to return"),
    db: Session = Depends(get_db),
) -> list[AssetPriceHistoryResponse]:
    """Get price history for an asset.

    Args:
        asset_id: ID of the asset.
        start_date: Optional filter for prices after this date.
        end_date: Optional filter for prices before this date.
        limit: Maximum number of records to return (max 1000).
        db: Database session.

    Returns:
        List of price history records, newest first.

    Raises:
        HTTPException: 404 if asset not found.
    """
    # Validate asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=404, detail=f"Asset with id {asset_id} not found"
        )

    return crud.get_asset_price_history(
        db=db, asset_id=asset_id, start_date=start_date, end_date=end_date, limit=limit
    )


@router.get("/assets/{asset_id}/chart", response_model=AssetPriceChartResponse)
def get_price_chart_data(
    asset_id: int,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
) -> AssetPriceChartResponse:
    """Get price data formatted for charting.

    Returns data points in chronological order (oldest first)
    suitable for time-series charts.

    Args:
        asset_id: ID of the asset.
        start_date: Optional filter for prices after this date.
        end_date: Optional filter for prices before this date.
        db: Database session.

    Returns:
        Chart data with asset info and chronologically ordered price points.

    Raises:
        HTTPException: 404 if asset not found.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    history = crud.get_asset_price_history(
        db=db, asset_id=asset_id, start_date=start_date, end_date=end_date, limit=1000
    )

    # Reverse to chronological order for charting
    data_points = [
        AssetPriceChartPoint(price=h.price, recorded_at=h.recorded_at)
        for h in reversed(history)
    ]

    return AssetPriceChartResponse(
        asset_id=asset_id,
        asset_name=asset.name,
        currency=history[0].currency if history else "USD",
        data_points=data_points,
    )
