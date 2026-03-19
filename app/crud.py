"""Database CRUD operations."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import AssetNotFoundError
from app.models import Asset, AssetPriceHistory


def record_asset_price(
    db: Session,
    asset_id: int,
    price: Decimal,
    recorded_at: datetime,
    currency: str = "USD",
    source: str | None = None,
    update_current_price: bool = True,
) -> AssetPriceHistory:
    """Record a new price for an asset.

    Args:
        db: Database session.
        asset_id: ID of the asset.
        price: The price value.
        recorded_at: When this price was valid.
        currency: Currency code (default USD).
        source: Source of the price data (e.g., 'yahoo', 'manual').
        update_current_price: If True, also update Asset.price.

    Returns:
        The created AssetPriceHistory record.

    Raises:
        AssetNotFoundError: If the asset with the given asset_id does not exist.
    """
    # Verify asset exists before creating price history
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise AssetNotFoundError(f"Asset with id {asset_id} not found")

    price_record = AssetPriceHistory(
        asset_id=asset_id,
        price=price,
        currency=currency,
        source=source,
        recorded_at=recorded_at,
    )
    db.add(price_record)

    if update_current_price:
        asset.price = price

    db.commit()
    db.refresh(price_record)
    return price_record


def get_asset_price_history(
    db: Session,
    asset_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
) -> list[AssetPriceHistory]:
    """Get price history for an asset.

    Args:
        db: Database session.
        asset_id: ID of the asset.
        start_date: Filter prices after this date.
        end_date: Filter prices before this date.
        limit: Maximum number of records to return.

    Returns:
        List of price history records, newest first.
    """
    query = db.query(AssetPriceHistory).filter(AssetPriceHistory.asset_id == asset_id)

    if start_date:
        query = query.filter(AssetPriceHistory.recorded_at >= start_date)
    if end_date:
        query = query.filter(AssetPriceHistory.recorded_at <= end_date)

    return query.order_by(AssetPriceHistory.recorded_at.desc()).limit(limit).all()


def get_latest_price(db: Session, asset_id: int) -> AssetPriceHistory | None:
    """Get the most recent price record for an asset.

    Args:
        db: Database session.
        asset_id: ID of the asset.

    Returns:
        The latest price record or None.
    """
    return (
        db.query(AssetPriceHistory)
        .filter(AssetPriceHistory.asset_id == asset_id)
        .order_by(AssetPriceHistory.recorded_at.desc())
        .first()
    )
