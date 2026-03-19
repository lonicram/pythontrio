"""Pytest configuration and shared fixtures."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign key support in SQLite for cascade deletes
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore
    """Enable foreign key support in SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test.

    Yields:
        Database session with tables created.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database dependency.

    Args:
        db_session: Test database session.

    Yields:
        FastAPI test client.
    """

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_portfolio(db_session: Session) -> dict:
    """Create a sample portfolio for testing.

    Args:
        db_session: Test database session.

    Returns:
        Dictionary with portfolio data including id.
    """
    from app.models import Portfolio

    portfolio = Portfolio(name="Test Portfolio", description="Test Description")
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "description": portfolio.description,
    }


@pytest.fixture
def sample_asset(db_session: Session, sample_portfolio: dict) -> dict:
    """Create a sample asset for testing.

    Args:
        db_session: Test database session.
        sample_portfolio: Portfolio fixture.

    Returns:
        Dictionary with asset data including id.
    """
    from decimal import Decimal

    from app.models import Asset

    asset = Asset(
        name="Apple Inc.",
        description="Technology company",
        code="AAPL",
        type="stock",
        price=Decimal("150.00"),
        portfolio_id=sample_portfolio["id"],
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return {
        "id": asset.id,
        "name": asset.name,
        "code": asset.code,
        "price": float(asset.price),
        "portfolio_id": asset.portfolio_id,
    }
