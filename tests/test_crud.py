"""Tests for CRUD operations."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app import crud
from app.exceptions import AssetNotFoundError
from app.models import AssetPriceHistory

# ============================================================================
# UNIT TESTS - CRUD Operations
# ============================================================================


def test_record_price_creates_history_record(
    db_session: Session, sample_asset: dict
) -> None:
    """Test that recording a price creates a history record."""
    price = Decimal("155.50")
    recorded_at = datetime(2024, 1, 15, 14, 30, 0)

    result = crud.record_asset_price(
        db=db_session,
        asset_id=sample_asset["id"],
        price=price,
        recorded_at=recorded_at,
        source="manual",
    )

    assert result.id is not None
    assert result.asset_id == sample_asset["id"]
    assert result.price == price
    assert result.currency == "USD"
    assert result.source == "manual"
    assert result.recorded_at == recorded_at
    assert result.created_at is not None


def test_record_price_updates_asset_current_price(
    db_session: Session, sample_asset: dict
) -> None:
    """Test that recording a price updates the Asset.price field."""
    from app.models import Asset

    original_price = Decimal("150.00")
    new_price = Decimal("155.50")
    recorded_at = datetime(2024, 1, 15, 14, 30, 0)

    # Verify original price
    asset = db_session.query(Asset).filter(Asset.id == sample_asset["id"]).first()
    assert asset.price == original_price

    # Record new price
    crud.record_asset_price(
        db=db_session,
        asset_id=sample_asset["id"],
        price=new_price,
        recorded_at=recorded_at,
    )

    # Verify price was updated
    db_session.refresh(asset)
    assert asset.price == new_price


def test_record_price_without_updating_current_price(
    db_session: Session, sample_asset: dict
) -> None:
    """Test recording historical price without updating Asset.price."""
    from app.models import Asset

    original_price = Decimal("150.00")
    historical_price = Decimal("140.00")
    recorded_at = datetime(2024, 1, 1, 0, 0, 0)

    # Record historical price without updating current
    crud.record_asset_price(
        db=db_session,
        asset_id=sample_asset["id"],
        price=historical_price,
        recorded_at=recorded_at,
        update_current_price=False,
    )

    # Verify Asset.price unchanged
    asset = db_session.query(Asset).filter(Asset.id == sample_asset["id"]).first()
    assert asset.price == original_price

    # Verify history record was created
    history = (
        db_session.query(AssetPriceHistory)
        .filter(AssetPriceHistory.asset_id == sample_asset["id"])
        .first()
    )
    assert history.price == historical_price


@pytest.mark.parametrize(
    "currency",
    ["USD", "EUR", "GBP", "JPY", "CHF"],
    ids=["usd", "eur", "gbp", "jpy", "chf"],
)
def test_record_price_currencies(
    db_session: Session, sample_asset: dict, currency: str
) -> None:
    """Test recording prices with various currency codes.

    Args:
        db_session: Database session.
        sample_asset: Sample asset fixture.
        currency: The currency code to test.
    """
    result = crud.record_asset_price(
        db=db_session,
        asset_id=sample_asset["id"],
        price=Decimal("130.25"),
        recorded_at=datetime(2024, 1, 15, 14, 30, 0),
        currency=currency,
    )

    assert result.currency == currency


def test_record_price_raises_error_for_nonexistent_asset(
    db_session: Session,
) -> None:
    """Test that recording price for non-existent asset raises AssetNotFoundError."""
    with pytest.raises(AssetNotFoundError) as exc_info:
        crud.record_asset_price(
            db=db_session,
            asset_id=99999,
            price=Decimal("100.00"),
            recorded_at=datetime(2024, 1, 15, 14, 30, 0),
        )

    assert "Asset with id 99999 not found" in str(exc_info.value)


def test_get_empty_history(db_session: Session, sample_asset: dict) -> None:
    """Test getting history for asset with no price records."""
    history = crud.get_asset_price_history(db=db_session, asset_id=sample_asset["id"])
    assert history == []


def test_get_history_returns_newest_first(
    db_session: Session, sample_asset: dict
) -> None:
    """Test that history is returned in descending order by recorded_at."""
    dates = [
        datetime(2024, 1, 1, 0, 0, 0),
        datetime(2024, 1, 2, 0, 0, 0),
        datetime(2024, 1, 3, 0, 0, 0),
    ]

    # Create records in random order
    for i, date in enumerate([dates[1], dates[0], dates[2]]):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=date,
            update_current_price=False,
        )

    history = crud.get_asset_price_history(db=db_session, asset_id=sample_asset["id"])

    # Should be ordered newest to oldest
    assert len(history) == 3
    assert history[0].recorded_at == dates[2]  # Jan 3
    assert history[1].recorded_at == dates[1]  # Jan 2
    assert history[2].recorded_at == dates[0]  # Jan 1


@pytest.mark.parametrize(
    "start_offset,end_offset,expected_count",
    [
        (None, None, 5),  # no filters, all 5 records
        (1, None, 4),  # from day 1, skip day 0
        (None, 3, 4),  # until day 3, include days 0-3
        (1, 3, 3),  # from day 1 to day 3, include days 1-3
    ],
    ids=["no_filters", "start_only", "end_only", "start_and_end"],
)
def test_get_history_date_filters(
    db_session: Session,
    sample_asset: dict,
    start_offset: int | None,
    end_offset: int | None,
    expected_count: int,
) -> None:
    """Test filtering price history by date range combinations.

    Args:
        db_session: Database session.
        sample_asset: Sample asset fixture.
        start_offset: Days offset for start_date (None for no filter).
        end_offset: Days offset for end_date (None for no filter).
        expected_count: Expected number of records returned.
    """
    base_date = datetime(2024, 1, 1, 0, 0, 0)

    # Create 5 daily price records
    for i in range(5):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=base_date + timedelta(days=i),
            update_current_price=False,
        )

    # Build filter parameters
    start_date = (
        (base_date + timedelta(days=start_offset)) if start_offset is not None else None
    )
    end_date = (
        (base_date + timedelta(days=end_offset)) if end_offset is not None else None
    )

    history = crud.get_asset_price_history(
        db=db_session,
        asset_id=sample_asset["id"],
        start_date=start_date,
        end_date=end_date,
    )

    assert len(history) == expected_count


def test_get_history_respects_limit(db_session: Session, sample_asset: dict) -> None:
    """Test that limit parameter caps number of returned records."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)

    # Create 10 records
    for i in range(10):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=base_time + timedelta(hours=i),
            update_current_price=False,
        )

    history = crud.get_asset_price_history(
        db=db_session, asset_id=sample_asset["id"], limit=5
    )

    assert len(history) == 5


def test_get_latest_price_returns_most_recent(
    db_session: Session, sample_asset: dict
) -> None:
    """Test that get_latest_price returns the most recent record."""
    dates = [
        datetime(2024, 1, 1, 0, 0, 0),
        datetime(2024, 1, 5, 0, 0, 0),
        datetime(2024, 1, 3, 0, 0, 0),
    ]

    for i, date in enumerate(dates):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=date,
            update_current_price=False,
        )

    latest = crud.get_latest_price(db=db_session, asset_id=sample_asset["id"])

    assert latest is not None
    assert latest.recorded_at == max(dates)
    assert latest.price == Decimal("151.00")  # Index 1 had Jan 5


def test_get_latest_price_returns_none_when_empty(
    db_session: Session, sample_asset: dict
) -> None:
    """Test that get_latest_price returns None when no history exists."""
    latest = crud.get_latest_price(db=db_session, asset_id=sample_asset["id"])
    assert latest is None


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.parametrize(
    "price",
    [
        Decimal("0.01"),  # minimum valid price
        Decimal("150.00"),  # normal price
        Decimal("9999999999.99"),  # maximum for DECIMAL(12,2)
    ],
    ids=["minimum", "normal", "maximum"],
)
def test_record_price_values(
    db_session: Session, sample_asset: dict, price: Decimal
) -> None:
    """Test handling various price values within valid range.

    Args:
        db_session: Database session.
        sample_asset: Sample asset fixture.
        price: The price value to test.
    """
    result = crud.record_asset_price(
        db=db_session,
        asset_id=sample_asset["id"],
        price=price,
        recorded_at=datetime(2024, 1, 15, 14, 30, 0),
    )

    assert result.price == price


def test_edge_case_same_recorded_at_timestamp(
    db_session: Session, sample_asset: dict
) -> None:
    """Test recording multiple prices with identical timestamps."""
    same_time = datetime(2024, 1, 15, 14, 30, 0)

    # Create two records with same timestamp
    for i in range(2):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=same_time,
            update_current_price=False,
        )

    history = crud.get_asset_price_history(db=db_session, asset_id=sample_asset["id"])

    # Both should exist
    assert len(history) == 2
    assert all(h.recorded_at == same_time for h in history)
