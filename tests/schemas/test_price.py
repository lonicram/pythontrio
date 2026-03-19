"""Tests for Asset Price History schemas."""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import AssetPriceHistoryCreate, AssetPriceHistoryResponse

# ============================================================================
# Price Validation Tests
# ============================================================================


@pytest.mark.parametrize(
    "price",
    [Decimal("0"), Decimal("-100.00"), Decimal("-0.01")],
    ids=["zero", "negative", "negative_fractional"],
)
def test_price_invalid_values_rejected(price: Decimal) -> None:
    """Test that invalid prices are rejected.

    Args:
        price: The invalid price to test.
    """
    with pytest.raises(ValidationError) as exc_info:
        AssetPriceHistoryCreate(
            asset_id=1,
            price=price,
            recorded_at=datetime.now(),
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "price must be greater than 0" in str(errors[0])


@pytest.mark.parametrize(
    "price",
    [
        Decimal("0.01"),  # minimum
        Decimal("100.00"),  # normal
        Decimal("150.50"),  # with cents
        Decimal("9999999999.99"),  # maximum
    ],
    ids=["minimum", "normal", "with_cents", "maximum"],
)
def test_price_valid_values_accepted(price: Decimal) -> None:
    """Test that valid prices are accepted.

    Args:
        price: The valid price to test.
    """
    schema = AssetPriceHistoryCreate(
        asset_id=1,
        price=price,
        recorded_at=datetime.now(),
    )

    assert schema.price == price


# ============================================================================
# Currency Validation Tests
# ============================================================================


@pytest.mark.parametrize(
    "currency",
    ["", "USDA", "TOOLONG"],
    ids=["empty", "too_long_4", "too_long_7"],
)
def test_currency_invalid_values_rejected(currency: str) -> None:
    """Test that invalid currency codes are rejected.

    Args:
        currency: The invalid currency code.
    """
    with pytest.raises(ValidationError) as exc_info:
        AssetPriceHistoryCreate(
            asset_id=1,
            price=Decimal("100.00"),
            currency=currency,
            recorded_at=datetime.now(),
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "currency must be 1-3 characters" in str(errors[0])


@pytest.mark.parametrize(
    "currency",
    ["X", "XX", "USD", "EUR", "GBP", "JPY", "CHF"],
    ids=[
        "1_char",
        "2_char",
        "3_char_usd",
        "3_char_eur",
        "3_char_gbp",
        "3_char_jpy",
        "3_char_chf",
    ],
)
def test_currency_valid_lengths_accepted(currency: str) -> None:
    """Test that valid currency code lengths are accepted.

    Args:
        currency: The valid currency code.
    """
    schema = AssetPriceHistoryCreate(
        asset_id=1,
        price=Decimal("100.00"),
        currency=currency,
        recorded_at=datetime.now(),
    )

    assert len(schema.currency) == len(currency)
    assert schema.currency == currency.upper()


@pytest.mark.parametrize(
    "input_currency,expected_currency",
    [
        ("usd", "USD"),
        ("USD", "USD"),
        ("UsD", "USD"),
        ("eur", "EUR"),
        ("EuR", "EUR"),
        ("gbp", "GBP"),
        ("  usd  ", "USD"),
        ("  eur  ", "EUR"),
        ("\tusd\t", "USD"),
    ],
    ids=[
        "lowercase_usd",
        "uppercase_usd",
        "mixedcase_usd",
        "lowercase_eur",
        "mixedcase_eur",
        "lowercase_gbp",
        "spaces_usd",
        "spaces_eur",
        "tabs_usd",
    ],
)
def test_currency_normalization(
    input_currency: str,
    expected_currency: str,
) -> None:
    """Test that currency codes are normalized correctly.

    Args:
        input_currency: The input currency code.
        expected_currency: The expected normalized code.
    """
    schema = AssetPriceHistoryCreate(
        asset_id=1,
        price=Decimal("100.00"),
        currency=input_currency,
        recorded_at=datetime.now(),
    )

    assert schema.currency == expected_currency


# ============================================================================
# AssetPriceHistoryCreate Schema Tests
# ============================================================================


def test_asset_price_history_create_with_all_fields() -> None:
    """Test creating price history with all optional fields."""
    now = datetime.now()
    schema = AssetPriceHistoryCreate(
        asset_id=1,
        price=Decimal("150.50"),
        currency="USD",
        source="yahoo",
        recorded_at=now,
    )

    assert schema.asset_id == 1
    assert schema.price == Decimal("150.50")
    assert schema.currency == "USD"
    assert schema.source == "yahoo"
    assert schema.recorded_at == now


def test_asset_price_history_create_minimal_fields() -> None:
    """Test creating price history with only required fields."""
    now = datetime.now()
    schema = AssetPriceHistoryCreate(
        asset_id=1,
        price=Decimal("150.50"),
        recorded_at=now,
    )

    assert schema.asset_id == 1
    assert schema.price == Decimal("150.50")
    assert schema.currency == "USD"  # default
    assert schema.source is None
    assert schema.recorded_at == now


# ============================================================================
# AssetPriceHistoryResponse Schema Tests
# ============================================================================


def test_asset_price_history_response_structure() -> None:
    """Test that AssetPriceHistoryResponse has all required fields."""
    now = datetime.now()
    schema = AssetPriceHistoryResponse(
        id=1,
        asset_id=1,
        price=Decimal("150.50"),
        currency="USD",
        source="yahoo",
        recorded_at=now,
        created_at=now,
    )

    assert schema.id == 1
    assert schema.asset_id == 1
    assert schema.price == Decimal("150.50")
    assert schema.currency == "USD"
    assert schema.source == "yahoo"
    assert schema.recorded_at == now
    assert schema.created_at == now


# ============================================================================
# Edge Cases
# ============================================================================


def test_price_with_many_decimals_truncated() -> None:
    """Test that prices with more than 2 decimal places are handled."""
    # Decimal is flexible - it should accept the value
    price_value = Decimal("100.999")
    schema = AssetPriceHistoryCreate(
        asset_id=1,
        price=price_value,
        recorded_at=datetime.now(),
    )

    # Decimal preserves the full precision
    assert schema.price == price_value


def test_source_optional_field() -> None:
    """Test that source field is optional."""
    schema_without_source = AssetPriceHistoryCreate(
        asset_id=1,
        price=Decimal("100.00"),
        recorded_at=datetime.now(),
    )
    assert schema_without_source.source is None

    schema_with_source = AssetPriceHistoryCreate(
        asset_id=1,
        price=Decimal("100.00"),
        source="manual",
        recorded_at=datetime.now(),
    )
    assert schema_with_source.source == "manual"
