"""Integration tests for portfolio holdings API endpoints."""

from decimal import Decimal

from fastapi.testclient import TestClient


def test_list_holdings_empty(client: TestClient, created_portfolio: dict) -> None:
    """Test that GET /portfolios/{id}/holdings returns empty list when no holdings.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.

    Verifies:
        - Response status code is 200.
        - Response body is an empty list.
    """
    portfolio_id = created_portfolio["id"]

    response = client.get(f"/portfolios/{portfolio_id}/holdings")

    assert response.status_code == 200
    assert response.json() == []


def test_add_holding(
    client: TestClient, created_portfolio: dict, created_asset: dict
) -> None:
    """Test that POST /portfolios/{id}/holdings creates a holding.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 201.
        - Response contains holding with assigned ID.
        - Holding references correct portfolio and asset.
        - Quantity matches the request payload.
    """
    portfolio_id = created_portfolio["id"]
    asset_id = created_asset["id"]
    payload = {
        "asset_id": asset_id,
        "quantity": "10.5",
        "purchase_price": "100.00",
    }

    response = client.post(f"/portfolios/{portfolio_id}/holdings", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["portfolio_id"] == portfolio_id
    assert data["asset_id"] == asset_id
    assert Decimal(data["quantity"]) == Decimal("10.5")
    assert Decimal(data["purchase_price"]) == Decimal("100.00")
    assert "asset" in data
    assert data["asset"]["id"] == asset_id


def test_add_holding_portfolio_not_found(
    client: TestClient, created_asset: dict
) -> None:
    """Test that POST /portfolios/{id}/holdings returns 404 if portfolio not found.

    Args:
        client: FastAPI test client fixture.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    payload = {
        "asset_id": created_asset["id"],
        "quantity": "10.0",
    }

    response = client.post("/portfolios/99999/holdings", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"


def test_add_holding_asset_not_found(
    client: TestClient, created_portfolio: dict
) -> None:
    """Test that POST /portfolios/{id}/holdings returns 404 if asset not found.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    portfolio_id = created_portfolio["id"]
    payload = {
        "asset_id": 99999,
        "quantity": "10.0",
    }

    response = client.post(f"/portfolios/{portfolio_id}/holdings", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_add_holding_duplicate(
    client: TestClient, created_portfolio: dict, created_asset: dict
) -> None:
    """Test that POST /portfolios/{id}/holdings returns 409 for duplicate holding.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - First request succeeds with status code 201.
        - Second request with same asset returns 409.
        - Response contains appropriate conflict error detail.
    """
    portfolio_id = created_portfolio["id"]
    asset_id = created_asset["id"]
    payload = {
        "asset_id": asset_id,
        "quantity": "5.0",
    }

    first_response = client.post(f"/portfolios/{portfolio_id}/holdings", json=payload)
    assert first_response.status_code == 201

    second_response = client.post(f"/portfolios/{portfolio_id}/holdings", json=payload)

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Asset already in portfolio"


def test_update_holding_quantity(
    client: TestClient, created_portfolio: dict, created_asset: dict
) -> None:
    """Test that PUT /portfolios/{id}/holdings/{asset_id} modifies quantity.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 200.
        - Quantity is updated to the new value.
        - Other holding properties remain unchanged.
    """
    portfolio_id = created_portfolio["id"]
    asset_id = created_asset["id"]
    create_payload = {
        "asset_id": asset_id,
        "quantity": "10.0",
        "purchase_price": "100.00",
    }
    create_response = client.post(
        f"/portfolios/{portfolio_id}/holdings", json=create_payload
    )
    assert create_response.status_code == 201

    update_payload = {"quantity": "25.5"}
    response = client.put(
        f"/portfolios/{portfolio_id}/holdings/{asset_id}", json=update_payload
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["quantity"]) == Decimal("25.5")
    assert Decimal(data["purchase_price"]) == Decimal("100.00")
    assert data["portfolio_id"] == portfolio_id
    assert data["asset_id"] == asset_id


def test_update_holding_not_found(
    client: TestClient, created_portfolio: dict
) -> None:
    """Test that PUT /portfolios/{id}/holdings/{asset_id} returns 404 for non-existent holding.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    portfolio_id = created_portfolio["id"]
    update_payload = {"quantity": "5.0"}

    response = client.put(
        f"/portfolios/{portfolio_id}/holdings/99999", json=update_payload
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Holding not found"


def test_remove_holding(
    client: TestClient, created_portfolio: dict, created_asset: dict
) -> None:
    """Test that DELETE /portfolios/{id}/holdings/{asset_id} removes holding.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.
        created_asset: Fixture providing a pre-created asset.

    Verifies:
        - Response status code is 204 (No Content).
        - Subsequent GET returns empty holdings list.
    """
    portfolio_id = created_portfolio["id"]
    asset_id = created_asset["id"]
    create_payload = {
        "asset_id": asset_id,
        "quantity": "10.0",
    }
    create_response = client.post(
        f"/portfolios/{portfolio_id}/holdings", json=create_payload
    )
    assert create_response.status_code == 201

    response = client.delete(f"/portfolios/{portfolio_id}/holdings/{asset_id}")

    assert response.status_code == 204

    list_response = client.get(f"/portfolios/{portfolio_id}/holdings")
    assert list_response.status_code == 200
    assert list_response.json() == []
