"""Tests for price history API endpoints."""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud

# ============================================================================
# INTEGRATION TESTS - API Endpoints
# ============================================================================


def test_api_record_price_success(client: TestClient, sample_asset: dict) -> None:
    """Test successfully recording a new price via API."""
    payload = {
        "asset_id": sample_asset["id"],
        "price": "155.50",
        "currency": "USD",
        "source": "yahoo",
        "recorded_at": "2024-01-15T14:30:00",
    }

    response = client.post("/prices/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["asset_id"] == sample_asset["id"]
    assert data["price"] == "155.50"
    assert data["currency"] == "USD"
    assert data["source"] == "yahoo"
    assert "id" in data
    assert "created_at" in data


def test_api_record_price_nonexistent_asset(client: TestClient) -> None:
    """Test recording price for non-existent asset returns 404."""
    payload = {
        "asset_id": 99999,
        "price": "100.00",
        "currency": "USD",
        "source": "manual",
        "recorded_at": "2024-01-15T14:30:00",
    }

    response = client.post("/prices/", json=payload)

    assert response.status_code == 404
    assert "Asset with id 99999 not found" in response.json()["detail"]


def test_api_record_price_invalid_data(client: TestClient, sample_asset: dict) -> None:
    """Test validation errors for invalid price data."""
    payload = {
        "asset_id": sample_asset["id"],
        "price": "not-a-number",
        "recorded_at": "2024-01-15T14:30:00",
    }

    response = client.post("/prices/", json=payload)

    assert response.status_code == 422  # Validation error


@pytest.mark.parametrize(
    "price",
    ["0", "-100.00", "-0.01"],
    ids=["zero", "negative", "negative_fractional"],
)
def test_api_record_price_invalid_prices_rejected(
    client: TestClient, sample_asset: dict, price: str
) -> None:
    """Test that invalid prices are rejected.

    Args:
        client: Test client.
        sample_asset: Sample asset fixture.
        price: The invalid price to test.
    """
    payload = {
        "asset_id": sample_asset["id"],
        "price": price,
        "currency": "USD",
        "source": "manual",
        "recorded_at": "2024-01-15T14:30:00",
    }

    response = client.post("/prices/", json=payload)

    assert response.status_code == 422
    assert "price must be greater than 0" in str(response.json())


@pytest.mark.parametrize(
    "currency",
    ["", "USDA", "TOOLONG"],
    ids=["empty", "too_long_4", "too_long_7"],
)
def test_api_record_price_invalid_currencies_rejected(
    client: TestClient, sample_asset: dict, currency: str
) -> None:
    """Test that invalid currency codes are rejected.

    Args:
        client: Test client.
        sample_asset: Sample asset fixture.
        currency: The invalid currency code to test.
    """
    payload = {
        "asset_id": sample_asset["id"],
        "price": "100.00",
        "currency": currency,
        "source": "manual",
        "recorded_at": "2024-01-15T14:30:00",
    }

    response = client.post("/prices/", json=payload)

    assert response.status_code == 422
    assert "currency must be 1-3 characters" in str(response.json())


@pytest.mark.parametrize(
    "input_currency,expected_currency",
    [
        ("usd", "USD"),
        ("USD", "USD"),
        ("UsD", "USD"),
        ("  eur  ", "EUR"),
        ("gbp", "GBP"),
    ],
    ids=["lowercase", "uppercase", "mixed_case", "with_whitespace", "lowercase_gbp"],
)
def test_api_record_price_currency_normalization(
    client: TestClient,
    sample_asset: dict,
    input_currency: str,
    expected_currency: str,
) -> None:
    """Test that currency codes are normalized correctly.

    Args:
        client: Test client.
        sample_asset: Sample asset fixture.
        input_currency: The input currency code.
        expected_currency: The expected normalized code.
    """
    payload = {
        "asset_id": sample_asset["id"],
        "price": "100.00",
        "currency": input_currency,
        "source": "manual",
        "recorded_at": "2024-01-15T14:30:00",
    }

    response = client.post("/prices/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["currency"] == expected_currency


def test_api_get_history_success(
    client: TestClient, db_session: Session, sample_asset: dict
) -> None:
    """Test retrieving price history via API."""
    # Create some history
    for i in range(3):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=datetime(2024, 1, i + 1, 0, 0, 0),
            update_current_price=False,
        )

    response = client.get(f"/prices/assets/{sample_asset['id']}/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(isinstance(record, dict) for record in data)
    assert all("price" in record for record in data)


def test_api_get_history_with_query_params(
    client: TestClient, db_session: Session, sample_asset: dict
) -> None:
    """Test filtering history with query parameters."""
    # Create 5 records
    for i in range(5):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=datetime(2024, 1, i + 1, 0, 0, 0),
            update_current_price=False,
        )

    # Request with limit
    response = client.get(f"/prices/assets/{sample_asset['id']}/history?limit=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_api_get_history_empty(client: TestClient, sample_asset: dict) -> None:
    """Test getting history for asset with no records."""
    response = client.get(f"/prices/assets/{sample_asset['id']}/history")

    assert response.status_code == 200
    assert response.json() == []


def test_api_get_history_nonexistent_asset(client: TestClient) -> None:
    """Test getting history for non-existent asset returns 404."""
    response = client.get("/prices/assets/99999/history")

    assert response.status_code == 404
    assert "Asset with id 99999 not found" in response.json()["detail"]


def test_api_get_chart_data_success(
    client: TestClient, db_session: Session, sample_asset: dict
) -> None:
    """Test retrieving chart data via API."""
    # Create history in reverse chronological order
    dates = [
        datetime(2024, 1, 3, 0, 0, 0),
        datetime(2024, 1, 1, 0, 0, 0),
        datetime(2024, 1, 2, 0, 0, 0),
    ]
    for i, date in enumerate(dates):
        crud.record_asset_price(
            db=db_session,
            asset_id=sample_asset["id"],
            price=Decimal(f"15{i}.00"),
            recorded_at=date,
            update_current_price=False,
        )

    response = client.get(f"/prices/assets/{sample_asset['id']}/chart")

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert data["asset_id"] == sample_asset["id"]
    assert data["asset_name"] == sample_asset["name"]
    assert data["currency"] == "USD"
    assert "data_points" in data

    # Check chronological order (oldest first)
    points = data["data_points"]
    assert len(points) == 3
    recorded_dates = [p["recorded_at"] for p in points]
    assert recorded_dates == sorted(recorded_dates)  # Should be ascending


def test_api_get_chart_nonexistent_asset(client: TestClient) -> None:
    """Test getting chart for non-existent asset returns 404."""
    response = client.get("/prices/assets/99999/chart")

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_api_get_chart_empty_history(client: TestClient, sample_asset: dict) -> None:
    """Test getting chart data for asset with no price history."""
    response = client.get(f"/prices/assets/{sample_asset['id']}/chart")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == sample_asset["id"]
    assert data["data_points"] == []
    assert data["currency"] == "USD"  # Default currency
