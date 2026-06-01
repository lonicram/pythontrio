"""Integration tests for assets API endpoints."""

from decimal import Decimal

from fastapi.testclient import TestClient

# ID that should never exist in the test database
NON_EXISTENT_ID = 99999


def test_list_assets_empty(client: TestClient) -> None:
    """Test that listing assets returns an empty list when no assets exist.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 200.
        - Response body is an empty list.
    """
    response = client.get("/assets/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_asset(client: TestClient) -> None:
    """Test that creating an asset returns the created asset.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 201.
        - Response contains the asset with correct fields.
        - Asset has an assigned ID.
    """
    payload = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "asset_type": "crypto",
        "description": "The first cryptocurrency",
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "BTC"
    assert data["name"] == "Bitcoin"
    assert data["asset_type"] == "crypto"
    assert data["description"] == "The first cryptocurrency"
    assert "id" in data
    assert isinstance(data["id"], int)


def test_create_asset_with_price(client: TestClient) -> None:
    """Test that creating an asset with a decimal price stores it correctly.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 201.
        - The price field is stored with correct decimal precision.
    """
    payload = {
        "symbol": "ETH",
        "name": "Ethereum",
        "asset_type": "crypto",
        "price": "2500.50",
    }

    response = client.post("/assets/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "ETH"
    assert data["name"] == "Ethereum"
    assert Decimal(data["price"]) == Decimal("2500.50")


def test_get_asset_by_id(client: TestClient, created_asset: dict) -> None:
    """Test that retrieving an asset by ID returns the correct asset.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset via API.

    Verifies:
        - Response status code is 200.
        - Response contains the asset matching the requested ID.
    """
    asset_id = created_asset["id"]

    response = client.get(f"/assets/{asset_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == asset_id
    assert data["symbol"] == created_asset["symbol"]
    assert data["name"] == created_asset["name"]


def test_get_asset_not_found(client: TestClient) -> None:
    """Test that retrieving a non-existent asset returns 404.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    response = client.get(f"/assets/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_update_asset(client: TestClient, created_asset: dict) -> None:
    """Test that updating an asset modifies its fields correctly.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset via API.

    Verifies:
        - Response status code is 200.
        - Updated fields reflect the new values.
        - Asset ID remains unchanged.
    """
    asset_id = created_asset["id"]

    update_payload = {
        "symbol": created_asset["symbol"],
        "name": "Updated Asset Name",
        "asset_type": "crypto",
        "description": "An updated description",
        "price": "0.45",
    }
    response = client.put(f"/assets/{asset_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == asset_id
    assert data["name"] == "Updated Asset Name"
    assert data["description"] == "An updated description"
    assert Decimal(data["price"]) == Decimal("0.45")


def test_update_asset_not_found(client: TestClient) -> None:
    """Test that updating a non-existent asset returns 404.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    update_payload = {
        "symbol": "FAKE",
        "name": "Fake Coin",
        "asset_type": "crypto",
    }

    response = client.put(f"/assets/{NON_EXISTENT_ID}", json=update_payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_delete_asset(client: TestClient, created_asset: dict) -> None:
    """Test that deleting an asset removes it from the database.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset via API.

    Verifies:
        - Delete response status code is 204.
        - Subsequent GET for the asset returns 404.
    """
    asset_id = created_asset["id"]

    delete_response = client.delete(f"/assets/{asset_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/assets/{asset_id}")
    assert get_response.status_code == 404


def test_delete_asset_not_found(client: TestClient) -> None:
    """Test that deleting a non-existent asset returns 404.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    response = client.delete(f"/assets/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"
