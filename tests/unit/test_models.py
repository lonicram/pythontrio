"""Unit tests for SQLAlchemy models."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding


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
