"""Tests for Asset model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import AssetPriceHistory

# ============================================================================
# MODEL TESTS - Asset
# ============================================================================


def test_model_asset_relationship(db_session: Session, sample_asset: dict) -> None:
    """Test that price history can access its parent asset."""
    price_record = AssetPriceHistory(
        asset_id=sample_asset["id"],
        price=Decimal("150.00"),
        currency="USD",
        recorded_at=datetime(2024, 1, 15, 14, 30, 0),
    )
    db_session.add(price_record)
    db_session.commit()
    db_session.refresh(price_record)

    # Access asset via relationship
    assert price_record.asset is not None
    assert price_record.asset.name == sample_asset["name"]
    assert price_record.asset.id == sample_asset["id"]
