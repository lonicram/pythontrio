"""Tests for Asset schemas."""

from decimal import Decimal

import pytest

from app.schemas import AssetCreate, AssetResponse

# ============================================================================
# Asset Schema Validation Tests
# ============================================================================


@pytest.mark.parametrize(
    "name,code,asset_type",
    [
        ("Apple Inc.", "AAPL", "stock"),
        ("Bitcoin", "BTC", "crypto"),
        ("Gold", "GOLD", "commodity"),
    ],
    ids=["stock", "crypto", "commodity"],
)
def test_asset_create_valid_types(name: str, code: str, asset_type: str) -> None:
    """Test creating assets with various types.

    Args:
        name: Asset name.
        code: Asset code.
        asset_type: Asset type.
    """
    asset = AssetCreate(
        name=name,
        code=code,
        type=asset_type,
        portfolio_id=1,
    )

    assert asset.name == name
    assert asset.code == code
    assert asset.type == asset_type
    assert asset.portfolio_id == 1


@pytest.mark.parametrize(
    "price",
    [None, Decimal("100.00"), Decimal("0.01"), Decimal("9999999999.99")],
    ids=["none", "normal", "minimum", "maximum"],
)
def test_asset_create_various_prices(price: Decimal | None) -> None:
    """Test creating assets with various price values.

    Args:
        price: The price value to test (can be None).
    """
    asset = AssetCreate(
        name="Test Asset",
        code="TEST",
        type="stock",
        portfolio_id=1,
        price=price,
    )

    assert asset.price == price


def test_asset_response_includes_id() -> None:
    """Test that AssetResponse includes required database fields."""
    asset = AssetResponse(
        id=1,
        name="Apple Inc.",
        code="AAPL",
        type="stock",
        portfolio_id=1,
    )

    assert asset.id == 1
    assert asset.name == "Apple Inc."
    assert asset.code == "AAPL"


def test_asset_create_optional_description() -> None:
    """Test that description is optional in AssetCreate."""
    asset_without_desc = AssetCreate(
        name="Test",
        code="TST",
        type="stock",
        portfolio_id=1,
    )
    assert asset_without_desc.description is None

    asset_with_desc = AssetCreate(
        name="Test",
        code="TST",
        type="stock",
        portfolio_id=1,
        description="A test asset",
    )
    assert asset_with_desc.description == "A test asset"
