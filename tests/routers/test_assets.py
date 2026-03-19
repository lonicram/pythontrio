"""Tests for Asset API endpoints."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Asset

# ============================================================================
# Asset List Tests
# ============================================================================


def test_list_assets_empty(client: TestClient) -> None:
    """Test listing assets when none exist."""
    response = client.get("/assets/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_assets_multiple(
    client: TestClient, db_session: Session, sample_portfolio: dict
) -> None:
    """Test listing multiple assets."""
    # Create multiple assets
    for i in range(3):
        asset = Asset(
            name=f"Asset {i}",
            code=f"AST{i}",
            type="stock",
            price=Decimal(f"{100 + i}.00"),
            portfolio_id=sample_portfolio["id"],
        )
        db_session.add(asset)
    db_session.commit()

    response = client.get("/assets/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("id" in asset for asset in data)
    assert all("name" in asset for asset in data)


# ============================================================================
# Get Single Asset Tests
# ============================================================================


def test_get_asset_success(client: TestClient, sample_asset: dict) -> None:
    """Test retrieving a single asset by ID."""
    response = client.get(f"/assets/{sample_asset['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_asset["id"]
    assert data["name"] == sample_asset["name"]
    assert data["code"] == sample_asset["code"]
    assert data["portfolio_id"] == sample_asset["portfolio_id"]


def test_get_asset_not_found(client: TestClient) -> None:
    """Test retrieving a non-existent asset returns 404."""
    response = client.get("/assets/99999")

    assert response.status_code == 404
    assert "Asset with id 99999 not found" in response.json()["detail"]


# ============================================================================
# Create Asset Tests
# ============================================================================


def test_create_asset_success(client: TestClient, sample_portfolio: dict) -> None:
    """Test successfully creating a new asset."""
    payload = {
        "name": "Apple Inc.",
        "code": "AAPL",
        "type": "stock",
        "portfolio_id": sample_portfolio["id"],
        "price": "150.00",
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Apple Inc."
    assert data["code"] == "AAPL"
    assert data["type"] == "stock"
    assert data["portfolio_id"] == sample_portfolio["id"]
    assert data["price"] == "150.00"
    assert "id" in data


def test_create_asset_with_description(
    client: TestClient, sample_portfolio: dict
) -> None:
    """Test creating an asset with description."""
    payload = {
        "name": "Bitcoin",
        "code": "BTC",
        "type": "crypto",
        "portfolio_id": sample_portfolio["id"],
        "description": "A cryptocurrency asset",
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "A cryptocurrency asset"


def test_create_asset_without_price(client: TestClient, sample_portfolio: dict) -> None:
    """Test creating an asset without initial price."""
    payload = {
        "name": "Gold",
        "code": "GOLD",
        "type": "commodity",
        "portfolio_id": sample_portfolio["id"],
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["price"] is None


def test_create_asset_nonexistent_portfolio(client: TestClient) -> None:
    """Test creating an asset with non-existent portfolio returns 400."""
    payload = {
        "name": "Test Asset",
        "code": "TST",
        "type": "stock",
        "portfolio_id": 99999,
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 400
    assert "Portfolio with id 99999 does not exist" in response.json()["detail"]


@pytest.mark.parametrize(
    "name,code,asset_type",
    [
        ("Apple Inc.", "AAPL", "stock"),
        ("Bitcoin", "BTC", "crypto"),
        ("Gold", "GOLD", "commodity"),
    ],
    ids=["stock", "crypto", "commodity"],
)
def test_create_asset_various_types(
    client: TestClient,
    sample_portfolio: dict,
    name: str,
    code: str,
    asset_type: str,
) -> None:
    """Test creating assets with various types.

    Args:
        client: Test client.
        sample_portfolio: Sample portfolio fixture.
        name: Asset name.
        code: Asset code.
        asset_type: Asset type.
    """
    payload = {
        "name": name,
        "code": code,
        "type": asset_type,
        "portfolio_id": sample_portfolio["id"],
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == asset_type
