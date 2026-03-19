"""Tests for AssetPriceHistory model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, AssetPriceHistory

# ============================================================================
# MODEL TESTS - AssetPriceHistory
# ============================================================================


def test_model_asset_price_history_relationship(
    db_session: Session, sample_asset: dict
) -> None:
    """Test that asset can access its price history."""
    # Create multiple price records
    for i in range(3):
        price_record = AssetPriceHistory(
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            currency="USD",
            recorded_at=datetime(2024, 1, i + 1, 0, 0, 0),
        )
        db_session.add(price_record)
    db_session.commit()

    # Access price history via asset
    asset = db_session.query(Asset).filter(Asset.id == sample_asset["id"]).first()
    assert len(asset.price_history) == 3

    # Verify ordering (should be desc by recorded_at)
    dates = [h.recorded_at for h in asset.price_history]
    assert dates == sorted(dates, reverse=True)
