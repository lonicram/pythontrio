"""Shared pytest fixtures for PythonTrio tests."""

from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.asset import Asset
from app.models.portfolio import Portfolio

# Default payload for creating test assets via API
DEFAULT_ASSET_PAYLOAD = {
    "symbol": "TEST",
    "name": "Test Asset",
    "asset_type": "crypto",
    "description": "A test asset for integration tests",
}


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Create in-memory SQLite engine for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient with overridden database dependency."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_portfolio(db_session: Session) -> Portfolio:
    """Create and return a sample portfolio.

    Args:
        db_session: SQLAlchemy session fixture for database operations.

    Returns:
        A persisted Portfolio instance.
    """
    portfolio = Portfolio(name="Test Portfolio")
    db_session.add(portfolio)
    db_session.flush()
    return portfolio


@pytest.fixture(scope="function")
def created_asset(client: TestClient) -> dict:
    """Create an asset via API and return the response data.

    Args:
        client: FastAPI test client fixture.

    Returns:
        A dict containing the created asset's data including its assigned ID.
    """
    response = client.post("/assets/", json=DEFAULT_ASSET_PAYLOAD)
    assert response.status_code == 201, f"Fixture setup failed: {response.json()}"
    return response.json()


@pytest.fixture(scope="function")
def sample_assets(db_session: Session) -> dict[str, Asset]:
    """Create BTC and ETH assets with standard test prices.

    Args:
        db_session: SQLAlchemy session fixture for database operations.

    Returns:
        A dict with 'btc' and 'eth' keys mapping to Asset instances.
    """
    btc = Asset(symbol="BTC", name="Bitcoin", price=Decimal("50000.00"))
    eth = Asset(symbol="ETH", name="Ethereum", price=Decimal("3000.00"))
    db_session.add_all([btc, eth])
    db_session.flush()
    return {"btc": btc, "eth": eth}


# Default payload for creating test portfolios via API
DEFAULT_PORTFOLIO_PAYLOAD = {
    "name": "Test Portfolio",
    "description": "A test portfolio for integration tests",
}


@pytest.fixture(scope="function")
def created_portfolio(client: TestClient) -> dict:
    """Create a portfolio via API and return the response data.

    Args:
        client: FastAPI test client fixture.

    Returns:
        A dict containing the created portfolio's data including its assigned ID.
    """
    response = client.post("/portfolios/", json=DEFAULT_PORTFOLIO_PAYLOAD)
    assert response.status_code == 201, f"Fixture setup failed: {response.json()}"
    return response.json()
