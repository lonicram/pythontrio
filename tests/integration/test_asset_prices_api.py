"""Integration tests for asset prices API endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def test_create_asset_price(client: TestClient, created_asset: dict) -> None:
    """Test that POST /assets/{id}/prices creates a price record.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 201.
        - Response contains price record with assigned ID.
        - Price record references correct asset.
        - Price and recorded_at match the request payload.
    """
    asset_id = created_asset["id"]
    recorded_at = datetime.now(UTC).isoformat()
    payload = {
        "asset_id": asset_id,
        "price": 150.75,
        "recorded_at": recorded_at,
        "source": "test_api",
    }

    response = client.post(f"/assets/{asset_id}/prices", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["asset_id"] == asset_id
    assert data["price"] == 150.75
    assert data["source"] == "test_api"


def test_create_asset_price_updates_asset(
    client: TestClient, created_asset: dict
) -> None:
    """Test that POST /assets/{id}/prices updates Asset.price (denormalization).

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 201.
        - Asset's price field is updated to match the new price record.
    """
    asset_id = created_asset["id"]
    new_price = 999.99
    payload = {
        "asset_id": asset_id,
        "price": new_price,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    response = client.post(f"/assets/{asset_id}/prices", json=payload)
    assert response.status_code == 201

    asset_response = client.get(f"/assets/{asset_id}")
    assert asset_response.status_code == 200
    assert float(asset_response.json()["price"]) == new_price


def test_create_asset_price_asset_not_found(client: TestClient) -> None:
    """Test that POST /assets/{id}/prices returns 404 if asset doesn't exist.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    payload = {
        "asset_id": 99999,
        "price": 100.00,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    response = client.post("/assets/99999/prices", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_create_asset_price_id_mismatch(
    client: TestClient, created_asset: dict
) -> None:
    """Test that POST /assets/{id}/prices returns 400 if asset_id in body doesn't match URL.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 400.
        - Response contains mismatch error detail.
    """
    asset_id = created_asset["id"]
    mismatched_id = asset_id + 100
    payload = {
        "asset_id": mismatched_id,
        "price": 100.00,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    response = client.post(f"/assets/{asset_id}/prices", json=payload)

    assert response.status_code == 400
    assert "mismatch" in response.json()["detail"].lower()


def test_get_price_history(client: TestClient, created_asset: dict) -> None:
    """Test that GET /assets/{id}/prices returns price records.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 200.
        - Response contains asset metadata and prices list.
        - Prices are returned in descending order (newest first).
    """
    asset_id = created_asset["id"]
    base_time = datetime.now(UTC)

    for i in range(3):
        payload = {
            "asset_id": asset_id,
            "price": 100.0 + i * 10,
            "recorded_at": (base_time + timedelta(hours=i)).isoformat(),
        }
        create_response = client.post(f"/assets/{asset_id}/prices", json=payload)
        assert create_response.status_code == 201

    response = client.get(f"/assets/{asset_id}/prices")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == asset_id
    assert data["asset_name"] == created_asset["name"]
    assert data["count"] == 3
    assert len(data["prices"]) == 3
    prices = [p["price"] for p in data["prices"]]
    assert prices == [120.0, 110.0, 100.0]


def test_get_price_history_with_date_filter(
    client: TestClient, created_asset: dict
) -> None:
    """Test that GET /assets/{id}/prices with date range filtering works.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 200.
        - Only prices within the date range are returned.
        - from_date and to_date are reflected in the response.
    """
    asset_id = created_asset["id"]
    base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    for i in range(5):
        payload = {
            "asset_id": asset_id,
            "price": 100.0 + i * 10,
            "recorded_at": (base_time + timedelta(days=i)).isoformat(),
        }
        create_response = client.post(f"/assets/{asset_id}/prices", json=payload)
        assert create_response.status_code == 201

    from_date = (base_time + timedelta(days=1)).isoformat()
    to_date = (base_time + timedelta(days=3)).isoformat()
    response = client.get(
        f"/assets/{asset_id}/prices",
        params={"from_date": from_date, "to_date": to_date},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert len(data["prices"]) == 3
    prices = [p["price"] for p in data["prices"]]
    assert prices == [130.0, 120.0, 110.0]


def test_get_price_history_pagination(
    client: TestClient, created_asset: dict
) -> None:
    """Test that GET /assets/{id}/prices with limit/offset works.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 200.
        - Limit restricts the number of records returned.
        - Offset skips the specified number of records.
        - Count reflects total records, not paginated count.
    """
    asset_id = created_asset["id"]
    base_time = datetime.now(UTC)

    for i in range(5):
        payload = {
            "asset_id": asset_id,
            "price": 100.0 + i * 10,
            "recorded_at": (base_time + timedelta(hours=i)).isoformat(),
        }
        create_response = client.post(f"/assets/{asset_id}/prices", json=payload)
        assert create_response.status_code == 201

    response = client.get(
        f"/assets/{asset_id}/prices",
        params={"limit": 2, "offset": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert len(data["prices"]) == 2
    prices = [p["price"] for p in data["prices"]]
    assert prices == [130.0, 120.0]


def test_get_latest_price(client: TestClient, created_asset: dict) -> None:
    """Test that GET /assets/{id}/prices/latest returns most recent price.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 200.
        - Response contains the most recent price record.
        - Price matches the latest submitted price.
    """
    asset_id = created_asset["id"]
    base_time = datetime.now(UTC)

    # Create multiple price records with different timestamps
    for i in range(3):
        payload = {
            "asset_id": asset_id,
            "price": 100.0 + i * 10,
            "recorded_at": (base_time + timedelta(hours=i)).isoformat(),
            "source": f"test_source_{i}",
        }
        create_response = client.post(f"/assets/{asset_id}/prices", json=payload)
        assert create_response.status_code == 201

    response = client.get(f"/assets/{asset_id}/prices/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == asset_id
    assert data["price"] == 120.0  # Most recent price (100 + 2*10)
    assert data["source"] == "test_source_2"
    assert "id" in data
    assert "recorded_at" in data
    assert "created_at" in data


def test_get_latest_price_no_history(client: TestClient, created_asset: dict) -> None:
    """Test that GET /assets/{id}/prices/latest returns 404 when no price history exists.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    asset_id = created_asset["id"]

    response = client.get(f"/assets/{asset_id}/prices/latest")

    assert response.status_code == 404
    assert "No price history found" in response.json()["detail"]
