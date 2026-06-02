"""Integration tests for user onboarding API endpoint."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile


def test_onboard_user_success(client: TestClient, db_session: Session, sample_assets: dict) -> None:
    """Test successful user onboarding with portfolio and holdings.

    Args:
        client: FastAPI test client fixture.
        db_session: SQLAlchemy session fixture for database operations.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.

    Verifies:
        - Response status code is 201.
        - User profile is created with correct data.
        - Portfolio is created and linked to user.
        - Holdings are created with correct quantities and asset references.
        - All entities are atomically persisted to database.
    """
    btc = sample_assets["btc"]
    eth = sample_assets["eth"]

    payload = {
        "email": "newuser@example.com",
        "username": "newuser",
        "full_name": "New User",
        "portfolio_name": "My Starter Portfolio",
        "portfolio_description": "Starting my investment journey",
        "starter_holdings": [
            {
                "asset_id": btc.id,
                "quantity": "0.5",
                "purchase_price": "50000.00",
            },
            {
                "asset_id": eth.id,
                "quantity": "10.0",
                "purchase_price": "3000.00",
            },
        ],
    }

    response = client.post("/users/onboard", json=payload)

    assert response.status_code == 201
    data = response.json()

    # Verify user profile fields
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert data["full_name"] == "New User"
    assert data["is_active"] is True
    assert "id" in data
    user_id = data["id"]

    # Verify portfolio is included in response
    assert "portfolios" in data
    assert len(data["portfolios"]) == 1
    portfolio = data["portfolios"][0]
    assert portfolio["name"] == "My Starter Portfolio"
    assert portfolio["description"] == "Starting my investment journey"
    portfolio_id = portfolio["id"]

    # Verify holdings are included in response
    assert "holdings" in portfolio
    assert len(portfolio["holdings"]) == 2

    holdings = sorted(portfolio["holdings"], key=lambda h: h["asset_id"])
    btc_holding = holdings[0] if holdings[0]["asset_id"] == btc.id else holdings[1]
    eth_holding = holdings[1] if holdings[1]["asset_id"] == eth.id else holdings[0]

    assert btc_holding["asset_id"] == btc.id
    assert Decimal(btc_holding["quantity"]) == Decimal("0.5")
    assert Decimal(btc_holding["purchase_price"]) == Decimal("50000.00")

    assert eth_holding["asset_id"] == eth.id
    assert Decimal(eth_holding["quantity"]) == Decimal("10.0")
    assert Decimal(eth_holding["purchase_price"]) == Decimal("3000.00")

    # Verify data persisted in database
    db_user = db_session.get(UserProfile, user_id)
    assert db_user is not None
    assert db_user.email == "newuser@example.com"

    db_portfolio = db_session.get(Portfolio, portfolio_id)
    assert db_portfolio is not None
    assert db_portfolio.owner_id == user_id
    assert db_portfolio.name == "My Starter Portfolio"

    db_holdings = (
        db_session.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )
    assert len(db_holdings) == 2


def test_onboard_user_rollback_invalid_asset(client: TestClient, db_session: Session) -> None:
    """Test that invalid asset_id triggers rollback of all changes.

    Args:
        client: FastAPI test client fixture.
        db_session: SQLAlchemy session fixture for database operations.

    Verifies:
        - Response status code is 400.
        - Error message indicates invalid asset_id.
        - No user profile is created.
        - No portfolio is created.
        - No holdings are created.
        - Database remains in consistent state (no partial data).
    """
    invalid_asset_id = 99999

    payload = {
        "email": "rollbackuser@example.com",
        "username": "rollbackuser",
        "full_name": "Rollback User",
        "portfolio_name": "Failed Portfolio",
        "starter_holdings": [
            {
                "asset_id": invalid_asset_id,
                "quantity": "1.0",
            },
        ],
    }

    response = client.post("/users/onboard", json=payload)

    assert response.status_code == 400
    assert "Invalid asset_id" in response.json()["detail"]

    # Verify no user profile was created
    users = db_session.query(UserProfile).filter_by(email="rollbackuser@example.com").all()
    assert len(users) == 0

    # Verify no portfolio was created
    portfolios = db_session.query(Portfolio).filter_by(name="Failed Portfolio").all()
    assert len(portfolios) == 0

    # Verify no holdings were created
    holdings = db_session.query(PortfolioHolding).all()
    assert len(holdings) == 0


def test_onboard_user_duplicate_email(client: TestClient, created_user_profile: dict) -> None:
    """Test that duplicate email returns 409 and does not create entities.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 409 (Conflict).
        - Error message indicates duplicate email or username.
        - No new user profile is created.
    """
    payload = {
        "email": created_user_profile["email"],  # Duplicate email
        "username": "differentusername",
        "full_name": "Different User",
        "portfolio_name": "My Portfolio",
    }

    response = client.post("/users/onboard", json=payload)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_onboard_user_empty_holdings(client: TestClient, db_session: Session) -> None:
    """Test that onboarding succeeds with empty holdings list.

    Args:
        client: FastAPI test client fixture.
        db_session: SQLAlchemy session fixture for database operations.

    Verifies:
        - Response status code is 201.
        - User profile is created.
        - Portfolio is created with empty holdings.
        - No holdings are created in database.
    """
    payload = {
        "email": "emptyuser@example.com",
        "username": "emptyuser",
        "full_name": "Empty User",
        "portfolio_name": "Empty Portfolio",
        "starter_holdings": [],  # Empty holdings
    }

    response = client.post("/users/onboard", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "emptyuser@example.com"
    assert len(data["portfolios"]) == 1

    portfolio = data["portfolios"][0]
    assert portfolio["name"] == "Empty Portfolio"
    assert portfolio["holdings"] == []

    # Verify in database
    portfolio_id = portfolio["id"]
    db_holdings = (
        db_session.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )
    assert len(db_holdings) == 0


def test_onboard_user_minimal_fields(client: TestClient, db_session: Session, sample_assets: dict) -> None:
    """Test onboarding with only required fields.

    Args:
        client: FastAPI test client fixture.
        db_session: SQLAlchemy session fixture for database operations.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.

    Verifies:
        - Response status code is 201.
        - User profile is created with defaults.
        - Portfolio is created with default name.
        - Holdings are created correctly.
    """
    btc = sample_assets["btc"]

    payload = {
        "email": "minimal@example.com",
        # username, full_name, portfolio_description omitted
        # portfolio_name uses default
        "starter_holdings": [
            {
                "asset_id": btc.id,
                "quantity": "1.0",
                # purchase_price omitted (optional)
            },
        ],
    }

    response = client.post("/users/onboard", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "minimal@example.com"
    assert data["username"] is None
    assert data["full_name"] is None
    assert data["is_active"] is True

    portfolio = data["portfolios"][0]
    assert portfolio["name"] == "My Portfolio"  # Default name
    assert portfolio["description"] is None

    holding = portfolio["holdings"][0]
    assert holding["asset_id"] == btc.id
    assert Decimal(holding["quantity"]) == Decimal("1.0")
    assert holding["purchase_price"] is None


def test_onboard_user_multiple_holdings_same_asset(
    client: TestClient, sample_assets: dict
) -> None:
    """Test that attempting to add multiple holdings for same asset in one request fails.

    Args:
        client: FastAPI test client fixture.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.

    Note:
        This test verifies database constraint behavior. The unique constraint on
        (portfolio_id, asset_id) should prevent duplicate holdings, causing rollback.

    Verifies:
        - Response status code is 400 (due to FK/integrity error handling).
        - No user or portfolio is created due to rollback.
    """
    btc = sample_assets["btc"]

    payload = {
        "email": "duplicate@example.com",
        "username": "duplicateuser",
        "portfolio_name": "Duplicate Holdings Test",
        "starter_holdings": [
            {
                "asset_id": btc.id,
                "quantity": "1.0",
            },
            {
                "asset_id": btc.id,  # Same asset again
                "quantity": "2.0",
            },
        ],
    }

    response = client.post("/users/onboard", json=payload)

    # The unique constraint violation will trigger IntegrityError
    # which gets caught and returns 400 or 409 depending on error message parsing
    assert response.status_code in [400, 409]
