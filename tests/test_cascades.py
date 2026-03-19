"""Tests for database cascade delete behavior."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app import crud
from app.models import Asset, AssetPriceHistory


def test_cascade_delete_price_history_when_asset_deleted(
    db_session: Session, sample_portfolio: dict
) -> None:
    """Test that price history records are deleted when their asset is deleted."""
    # Create an asset
    asset = Asset(
        name="Test Asset",
        code="TEST",
        type="stock",
        price=Decimal("100.00"),
        portfolio_id=sample_portfolio["id"],
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    # Record some prices
    for i in range(3):
        crud.record_asset_price(
            db=db_session,
            asset_id=asset.id,
            price=Decimal(f"{100 + i}.00"),
            recorded_at=datetime(2024, 1, i + 1, 0, 0, 0),
            update_current_price=False,
        )

    # Verify price history exists
    history = (
        db_session.query(AssetPriceHistory)
        .filter(AssetPriceHistory.asset_id == asset.id)
        .all()
    )
    assert len(history) == 3

    # Delete the asset
    db_session.delete(asset)
    db_session.commit()

    # Verify asset is deleted
    deleted_asset = db_session.query(Asset).filter(Asset.id == asset.id).first()
    assert deleted_asset is None

    # Verify price history was also deleted (cascade delete)
    orphaned_history = (
        db_session.query(AssetPriceHistory)
        .filter(AssetPriceHistory.asset_id == asset.id)
        .all()
    )
    assert len(orphaned_history) == 0
