"""Unit tests for SQLAlchemy models."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile


def test_asset_creation() -> None:
    """Test Asset model instantiation with all fields.

    Verifies:
        - Asset can be instantiated with all required and optional fields.
        - All field values are correctly assigned.
    """
    asset = Asset(
        id=1,
        symbol="BTC",
        name="Bitcoin",
        asset_type="crypto",
        description="The original cryptocurrency",
        price=Decimal("67500.12345678"),
    )

    assert asset.id == 1
    assert asset.symbol == "BTC"
    assert asset.name == "Bitcoin"
    assert asset.asset_type == "crypto"
    assert asset.description == "The original cryptocurrency"
    assert asset.price == Decimal("67500.12345678")


def test_asset_repr() -> None:
    """Test Asset __repr__ method returns expected string format."""
    asset = Asset(
        symbol="BTC",
        name="Bitcoin",
        price=Decimal("67500.12345678"),
    )

    assert repr(asset) == "<Asset(symbol=BTC, name=Bitcoin, price=67500.12345678)>"


def test_asset_creation_with_null_optional_fields() -> None:
    """Test Asset model instantiation with only required fields.

    Verifies:
        - Asset can be instantiated with only required fields.
        - Optional fields default to None.
    """
    asset = Asset(
        symbol="ETH",
        name="Ethereum",
    )

    assert asset.symbol == "ETH"
    assert asset.name == "Ethereum"
    assert asset.id is None
    assert asset.asset_type is None
    assert asset.description is None
    assert asset.price is None


def test_portfolio_total_value_empty(db_session: Session) -> None:
    """Test Portfolio.total_value returns 0 when portfolio has no holdings.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
    """
    portfolio = Portfolio(name="Empty Portfolio")
    db_session.add(portfolio)
    db_session.commit()

    assert portfolio.total_value == Decimal("0")


def test_portfolio_total_value_with_holdings(
    db_session: Session,
    sample_portfolio: Portfolio,
    sample_assets: dict[str, Asset],
) -> None:
    """Test Portfolio.total_value correctly sums holdings * asset prices.

    Creates a portfolio with two holdings and verifies the total value
    is calculated as sum of (quantity * price) for each holding.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_portfolio: Pre-created portfolio fixture.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.
    """
    btc = sample_assets["btc"]
    eth = sample_assets["eth"]

    # Add holdings: 2 BTC @ 50000 = 100000, 10 ETH @ 3000 = 30000
    holding_btc = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_id=btc.id,
        quantity=Decimal("2"),
    )
    holding_eth = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_id=eth.id,
        quantity=Decimal("10"),
    )
    db_session.add_all([holding_btc, holding_eth])
    db_session.commit()

    # Expected: (2 * 50000) + (10 * 3000) = 100000 + 30000 = 130000
    assert sample_portfolio.total_value == Decimal("130000.00")


def test_portfolio_total_value_ignores_null_prices(
    db_session: Session,
    sample_portfolio: Portfolio,
    sample_assets: dict[str, Asset],
) -> None:
    """Test Portfolio.total_value skips assets with null prices.

    Creates a portfolio with two holdings where one asset has a null price.
    Verifies that only holdings with priced assets contribute to total.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_portfolio: Pre-created portfolio fixture.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.
    """
    btc = sample_assets["btc"]

    # Create an asset without a price
    unknown = Asset(symbol="UNK", name="Unknown Asset", price=None)
    db_session.add(unknown)
    db_session.flush()

    # Add holdings for both assets
    holding_btc = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_id=btc.id,
        quantity=Decimal("2"),
    )
    holding_unknown = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_id=unknown.id,
        quantity=Decimal("100"),
    )
    db_session.add_all([holding_btc, holding_unknown])
    db_session.commit()

    # Expected: Only BTC counts: 2 * 50000 = 100000
    # Unknown asset with null price is ignored
    assert sample_portfolio.total_value == Decimal("100000.00")


def test_portfolio_total_value_with_zero_quantity_holding(
    db_session: Session,
    sample_portfolio: Portfolio,
    sample_assets: dict[str, Asset],
) -> None:
    """Test Portfolio.total_value correctly handles zero-quantity holdings.

    Verifies that holdings with zero quantity contribute zero to the total,
    and only non-zero holdings are counted.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_portfolio: Pre-created portfolio fixture.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.
    """
    btc = sample_assets["btc"]
    eth = sample_assets["eth"]

    # Add holdings: 2 BTC @ 50000 = 100000, 0 ETH @ 3000 = 0
    holding_btc = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_id=btc.id,
        quantity=Decimal("2"),
    )
    holding_eth_zero = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_id=eth.id,
        quantity=Decimal("0"),
    )
    db_session.add_all([holding_btc, holding_eth_zero])
    db_session.commit()

    # Expected: (2 * 50000) + (0 * 3000) = 100000 + 0 = 100000
    assert sample_portfolio.total_value == Decimal("100000.00")


def test_portfolio_holding_repr() -> None:
    """Test PortfolioHolding __repr__ method returns expected string format.

    Verifies the repr includes portfolio_id, asset_id, and quantity
    in the expected format.
    """
    holding = PortfolioHolding(
        portfolio_id=1,
        asset_id=42,
        quantity=Decimal("5.5"),
    )

    expected = "<PortfolioHolding(portfolio=1, asset=42, qty=5.5)>"
    assert repr(holding) == expected


def test_user_profile_creation() -> None:
    """Test UserProfile model instantiation with all fields."""
    user_profile = UserProfile(
        id=1,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
    )

    assert user_profile.id == 1
    assert user_profile.email == "test@example.com"
    assert user_profile.username == "testuser"
    assert user_profile.full_name == "Test User"
    assert user_profile.is_active is True


def test_user_profile_creation_minimal(db_session: Session) -> None:
    """Test UserProfile model with only required fields.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
    """
    user_profile = UserProfile(email="minimal@example.com")
    db_session.add(user_profile)
    db_session.commit()

    assert user_profile.email == "minimal@example.com"
    assert user_profile.username is None
    assert user_profile.full_name is None
    assert user_profile.is_active is True  # Server default applied by database


def test_user_profile_repr() -> None:
    """Test UserProfile __repr__ method returns expected string format."""
    user_profile = UserProfile(id=1, email="test@example.com", username="testuser")

    assert repr(user_profile) == "<UserProfile(id=1, email=test@example.com, username=testuser)>"


def test_user_profile_portfolio_relationship(db_session: Session) -> None:
    """Test UserProfile-Portfolio bidirectional relationship."""
    user_profile = UserProfile(email="owner@example.com")
    db_session.add(user_profile)
    db_session.flush()

    portfolio = Portfolio(name="User Portfolio", owner_id=user_profile.id)
    db_session.add(portfolio)
    db_session.flush()

    # Test bidirectional access
    assert portfolio.owner == user_profile
    assert portfolio in user_profile.portfolios


def test_user_profile_cascade_delete_portfolios(db_session: Session) -> None:
    """Test that deleting a user profile cascades to their portfolios."""
    user_profile = UserProfile(email="cascade@example.com")
    db_session.add(user_profile)
    db_session.flush()

    portfolio = Portfolio(name="Cascade Test", owner_id=user_profile.id)
    db_session.add(portfolio)
    db_session.commit()

    portfolio_id = portfolio.id
    db_session.delete(user_profile)
    db_session.commit()

    # Portfolio should be deleted
    assert db_session.get(Portfolio, portfolio_id) is None


def test_portfolio_without_owner(db_session: Session) -> None:
    """Test that portfolios can exist without an owner (backward compatibility)."""
    portfolio = Portfolio(name="Orphan Portfolio")
    db_session.add(portfolio)
    db_session.commit()

    assert portfolio.owner_id is None
    assert portfolio.owner is None
