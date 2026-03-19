"""Tests for Portfolio API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Portfolio

# ============================================================================
# Portfolio List Tests
# ============================================================================


def test_list_portfolios_empty(client: TestClient) -> None:
    """Test listing portfolios when none exist."""
    response = client.get("/portfolios/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_portfolios_multiple(client: TestClient, db_session: Session) -> None:
    """Test listing multiple portfolios."""
    # Create multiple portfolios
    for i in range(3):
        portfolio = Portfolio(name=f"Portfolio {i}", description=f"Test portfolio {i}")
        db_session.add(portfolio)
    db_session.commit()

    response = client.get("/portfolios/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("id" in p for p in data)
    assert all("name" in p for p in data)


# ============================================================================
# Get Single Portfolio Tests
# ============================================================================


def test_get_portfolio_success(client: TestClient, sample_portfolio: dict) -> None:
    """Test retrieving a single portfolio by ID."""
    response = client.get(f"/portfolios/{sample_portfolio['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_portfolio["id"]
    assert data["name"] == sample_portfolio["name"]


def test_get_portfolio_not_found(client: TestClient) -> None:
    """Test retrieving a non-existent portfolio returns 404."""
    response = client.get("/portfolios/99999")

    assert response.status_code == 404
    assert "Portfolio with id 99999 not found" in response.json()["detail"]


# ============================================================================
# Create Portfolio Tests
# ============================================================================


def test_create_portfolio_success(client: TestClient) -> None:
    """Test successfully creating a new portfolio."""
    payload = {
        "name": "My Investment Portfolio",
    }

    response = client.post("/portfolios/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Investment Portfolio"
    assert data["description"] is None
    assert "id" in data


def test_create_portfolio_with_description(client: TestClient) -> None:
    """Test creating a portfolio with description."""
    payload = {
        "name": "Retirement Fund",
        "description": "Long-term retirement investment portfolio",
    }

    response = client.post("/portfolios/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Retirement Fund"
    assert data["description"] == "Long-term retirement investment portfolio"


@pytest.mark.parametrize(
    "name",
    [
        "Personal Portfolio",
        "Retirement Fund",
        "Trading Portfolio",
        "Cryptocurrency Holdings",
    ],
    ids=["personal", "retirement", "trading", "crypto"],
)
def test_create_portfolio_various_names(client: TestClient, name: str) -> None:
    """Test creating portfolios with various names.

    Args:
        client: Test client.
        name: Portfolio name.
    """
    payload = {"name": name}

    response = client.post("/portfolios/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name


# ============================================================================
# Delete Portfolio Tests
# ============================================================================


def test_delete_portfolio_success(client: TestClient, db_session: Session) -> None:
    """Test successfully deleting a portfolio."""
    # Create a portfolio
    portfolio = Portfolio(name="Portfolio to Delete")
    db_session.add(portfolio)
    db_session.commit()
    portfolio_id = portfolio.id

    # Delete it
    response = client.delete(f"/portfolios/{portfolio_id}")

    assert response.status_code == 204

    # Verify it's deleted
    deleted_portfolio = (
        db_session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    )
    assert deleted_portfolio is None


def test_delete_portfolio_not_found(client: TestClient) -> None:
    """Test deleting a non-existent portfolio returns 404."""
    response = client.delete("/portfolios/99999")

    assert response.status_code == 404
    assert "Portfolio not found" in response.json()["detail"]
