"""Integration tests for portfolios API endpoints."""

from fastapi.testclient import TestClient

# ID that should not exist in the test database
NON_EXISTENT_ID = 99999


def test_list_portfolios_empty(client: TestClient) -> None:
    """Test that listing portfolios returns an empty list when none exist.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 200.
        - Response body is an empty list.
    """
    response = client.get("/portfolios/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_portfolio(client: TestClient) -> None:
    """Test that POST /portfolios/ creates and returns a portfolio.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 201.
        - Response contains the portfolio with assigned ID.
        - Portfolio fields match the request payload.
    """
    payload = {"name": "My Portfolio", "description": "Test description"}

    response = client.post("/portfolios/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]


def test_get_portfolio_by_id(client: TestClient, created_portfolio: dict) -> None:
    """Test that GET /portfolios/{id} returns the portfolio.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.

    Verifies:
        - Response status code is 200.
        - Response data matches the created portfolio.
    """
    portfolio_id = created_portfolio["id"]

    response = client.get(f"/portfolios/{portfolio_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == portfolio_id
    assert data["name"] == created_portfolio["name"]
    assert data["description"] == created_portfolio["description"]


def test_get_portfolio_not_found(client: TestClient) -> None:
    """Test that GET /portfolios/{id} returns 404 for non-existent portfolio.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    response = client.get(f"/portfolios/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"


def test_update_portfolio(client: TestClient, created_portfolio: dict) -> None:
    """Test that PUT /portfolios/{id} modifies portfolio fields.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.

    Verifies:
        - Response status code is 200.
        - Response reflects the updated fields.
        - Portfolio ID remains unchanged.
    """
    portfolio_id = created_portfolio["id"]
    update_payload = {"name": "Updated Portfolio", "description": "New description"}

    response = client.put(f"/portfolios/{portfolio_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == portfolio_id
    assert data["name"] == update_payload["name"]
    assert data["description"] == update_payload["description"]


def test_delete_portfolio(client: TestClient, created_portfolio: dict) -> None:
    """Test that DELETE /portfolios/{id} removes the portfolio.

    Args:
        client: FastAPI test client fixture.
        created_portfolio: Fixture providing a pre-created portfolio.

    Verifies:
        - Delete response status code is 204.
        - Subsequent GET returns 404.
    """
    portfolio_id = created_portfolio["id"]

    delete_response = client.delete(f"/portfolios/{portfolio_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/portfolios/{portfolio_id}")
    assert get_response.status_code == 404


def test_update_portfolio_not_found(client: TestClient) -> None:
    """Test that PUT /portfolios/{id} returns 404 for non-existent portfolio.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    update_payload = {"name": "Updated Portfolio", "description": "New description"}

    response = client.put(f"/portfolios/{NON_EXISTENT_ID}", json=update_payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"


def test_delete_portfolio_not_found(client: TestClient) -> None:
    """Test that DELETE /portfolios/{id} returns 404 for non-existent portfolio.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    response = client.delete(f"/portfolios/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"
