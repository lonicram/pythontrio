"""Unit tests for OnboardingService."""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, PropertyMock, call

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile
from app.schemas.onboarding import StarterHolding, UserOnboardRequest
from app.services.onboarding_service import OnboardingService


def test_onboard_user_creates_all_entities(db_session: Session, sample_assets: dict) -> None:
    """Test that OnboardingService.onboard_user creates user, portfolio, and holdings.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.

    Verifies:
        - User profile is created with correct attributes.
        - Portfolio is created and linked to user.
        - Holdings are created with correct asset references and quantities.
        - All entities are committed to database.
        - User object is refreshed and returned with eager-loaded relationships.
    """
    btc = sample_assets["btc"]
    eth = sample_assets["eth"]

    request = UserOnboardRequest(
        email="service@example.com",
        username="serviceuser",
        full_name="Service User",
        portfolio_name="Service Portfolio",
        portfolio_description="Created via service",
        starter_holdings=[
            StarterHolding(
                asset_id=btc.id,
                quantity=Decimal("0.5"),
                purchase_price=Decimal("50000.00"),
            ),
            StarterHolding(
                asset_id=eth.id,
                quantity=Decimal("10.0"),
                purchase_price=Decimal("3000.00"),
            ),
        ],
    )

    service = OnboardingService(db_session)
    result = service.onboard_user(request)

    # Verify returned user
    assert isinstance(result, UserProfile)
    assert result.email == "service@example.com"
    assert result.username == "serviceuser"
    assert result.full_name == "Service User"
    assert result.is_active is True
    assert result.id is not None

    # Verify user persisted in database
    db_user = db_session.get(UserProfile, result.id)
    assert db_user is not None
    assert db_user.email == "service@example.com"

    # Verify portfolio created
    assert len(db_user.portfolios) == 1
    portfolio = db_user.portfolios[0]
    assert portfolio.name == "Service Portfolio"
    assert portfolio.description == "Created via service"
    assert portfolio.owner_id == result.id

    # Verify holdings created
    assert len(portfolio.holdings) == 2
    holdings = sorted(portfolio.holdings, key=lambda h: h.asset_id)

    btc_holding = holdings[0] if holdings[0].asset_id == btc.id else holdings[1]
    eth_holding = holdings[1] if holdings[1].asset_id == eth.id else holdings[0]

    assert btc_holding.asset_id == btc.id
    assert btc_holding.quantity == Decimal("0.5")
    assert btc_holding.purchase_price == Decimal("50000.00")

    assert eth_holding.asset_id == eth.id
    assert eth_holding.quantity == Decimal("10.0")
    assert eth_holding.purchase_price == Decimal("3000.00")


def test_onboard_user_with_empty_holdings(db_session: Session) -> None:
    """Test that onboarding succeeds with empty holdings list.

    Args:
        db_session: SQLAlchemy session fixture for database operations.

    Verifies:
        - User and portfolio are created successfully.
        - Portfolio has no holdings.
    """
    request = UserOnboardRequest(
        email="empty@example.com",
        username="emptyuser",
        portfolio_name="Empty Portfolio",
        starter_holdings=[],
    )

    service = OnboardingService(db_session)
    result = service.onboard_user(request)

    assert result.email == "empty@example.com"
    assert len(result.portfolios) == 1
    assert result.portfolios[0].name == "Empty Portfolio"
    assert len(result.portfolios[0].holdings) == 0


def test_onboard_user_rollback_on_invalid_asset_id(db_session: Session) -> None:
    """Test that invalid asset_id triggers IntegrityError on commit and rolls back.

    Args:
        db_session: SQLAlchemy session fixture for database operations.

    Verifies:
        - Service returns user (no commit yet).
        - IntegrityError is raised when caller commits due to FK constraint.
        - No user profile is persisted after rollback.
        - No portfolio is persisted after rollback.
    """
    invalid_asset_id = 99999

    request = UserOnboardRequest(
        email="rollback@example.com",
        username="rollbackuser",
        portfolio_name="Rollback Portfolio",
        starter_holdings=[
            StarterHolding(
                asset_id=invalid_asset_id,
                quantity=Decimal("1.0"),
            ),
        ],
    )

    service = OnboardingService(db_session)

    # Service returns without error (no commit yet)
    user = service.onboard_user(request)
    assert user.email == "rollback@example.com"

    # IntegrityError raised when caller commits
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback to clear failed transaction
    db_session.rollback()

    # Verify rollback: no user should exist
    users = db_session.query(UserProfile).filter_by(email="rollback@example.com").all()
    assert len(users) == 0

    # Verify rollback: no portfolio should exist
    portfolios = db_session.query(Portfolio).filter_by(name="Rollback Portfolio").all()
    assert len(portfolios) == 0


def test_onboard_user_duplicate_email_raises_integrity_error(
    db_session: Session, sample_user_profile: UserProfile
) -> None:
    """Test that duplicate email raises IntegrityError.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_user_profile: Fixture providing a pre-created user profile.

    Verifies:
        - IntegrityError is raised when attempting to create user with duplicate email.
    """
    request = UserOnboardRequest(
        email=sample_user_profile.email,  # Duplicate email
        username="differentuser",
        portfolio_name="Different Portfolio",
        starter_holdings=[],
    )

    service = OnboardingService(db_session)

    with pytest.raises(IntegrityError):
        service.onboard_user(request)


def test_onboard_user_duplicate_username_raises_integrity_error(
    db_session: Session, sample_user_profile: UserProfile
) -> None:
    """Test that duplicate username raises IntegrityError.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_user_profile: Fixture providing a pre-created user profile.

    Verifies:
        - IntegrityError is raised when attempting to create user with duplicate username.
    """
    request = UserOnboardRequest(
        email="different@example.com",
        username=sample_user_profile.username,  # Duplicate username
        portfolio_name="Different Portfolio",
        starter_holdings=[],
    )

    service = OnboardingService(db_session)

    with pytest.raises(IntegrityError):
        service.onboard_user(request)


def test_onboard_user_service_calls_flush_not_commit() -> None:
    """Test that service calls flush but NOT commit (caller controls transaction).

    This test uses mocking to verify the sequence of database operations without
    actually persisting data.

    Verifies:
        - db.add() is called for user, portfolio, and holdings.
        - db.flush() is called after adding user and portfolio (to get IDs).
        - db.commit() is NOT called (caller responsibility).
        - db.refresh() is NOT called (caller responsibility).
    """
    mock_db = MagicMock(spec=Session)

    # Mock user creation - need to set id after flush
    def flush_side_effect() -> None:
        """Simulate database assigning IDs on flush."""
        for call_item in mock_db.add.call_args_list:
            obj = call_item[0][0]
            if isinstance(obj, UserProfile) and obj.id is None:
                obj.id = 1
            elif isinstance(obj, Portfolio) and obj.id is None:
                obj.id = 1

    mock_db.flush.side_effect = flush_side_effect

    request = UserOnboardRequest(
        email="mock@example.com",
        username="mockuser",
        portfolio_name="Mock Portfolio",
        starter_holdings=[
            StarterHolding(asset_id=1, quantity=Decimal("1.0")),
            StarterHolding(asset_id=2, quantity=Decimal("2.0")),
        ],
    )

    service = OnboardingService(mock_db)
    result = service.onboard_user(request)

    # Verify the sequence of operations
    assert mock_db.add.call_count == 4  # user + portfolio + 2 holdings
    assert mock_db.flush.call_count == 2  # after user, after portfolio

    # Service should NOT commit or refresh - caller controls transaction
    assert mock_db.commit.call_count == 0
    assert mock_db.refresh.call_count == 0


def test_onboard_user_with_purchase_price_none(db_session: Session, sample_assets: dict) -> None:
    """Test that holdings can be created without purchase_price.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.

    Verifies:
        - Holding is created with purchase_price as None.
    """
    btc = sample_assets["btc"]

    request = UserOnboardRequest(
        email="noprice@example.com",
        username="nopriceuser",
        portfolio_name="No Price Portfolio",
        starter_holdings=[
            StarterHolding(
                asset_id=btc.id,
                quantity=Decimal("1.0"),
                # purchase_price intentionally omitted
            ),
        ],
    )

    service = OnboardingService(db_session)
    result = service.onboard_user(request)

    assert len(result.portfolios[0].holdings) == 1
    holding = result.portfolios[0].holdings[0]
    assert holding.purchase_price is None
    assert holding.quantity == Decimal("1.0")


def test_onboard_user_sets_user_active_by_default(db_session: Session) -> None:
    """Test that new users are created with is_active=True by default.

    Args:
        db_session: SQLAlchemy session fixture for database operations.

    Verifies:
        - User profile is created with is_active=True.
    """
    request = UserOnboardRequest(
        email="active@example.com",
        username="activeuser",
        portfolio_name="Active Portfolio",
        starter_holdings=[],
    )

    service = OnboardingService(db_session)
    result = service.onboard_user(request)

    assert result.is_active is True

    # Verify in database (after server default is applied)
    db_user = db_session.get(UserProfile, result.id)
    assert db_user.is_active is True


def test_onboard_user_creates_portfolio_with_correct_owner(
    db_session: Session, sample_assets: dict
) -> None:
    """Test that portfolio is correctly linked to created user via owner_id.

    Args:
        db_session: SQLAlchemy session fixture for database operations.
        sample_assets: Dict containing 'btc' and 'eth' Asset fixtures.

    Verifies:
        - Portfolio owner_id matches user id.
        - Bidirectional relationship is established.
    """
    btc = sample_assets["btc"]

    request = UserOnboardRequest(
        email="owner@example.com",
        username="owneruser",
        portfolio_name="Owner Portfolio",
        starter_holdings=[
            StarterHolding(asset_id=btc.id, quantity=Decimal("1.0")),
        ],
    )

    service = OnboardingService(db_session)
    result = service.onboard_user(request)

    portfolio = result.portfolios[0]
    assert portfolio.owner_id == result.id
    assert portfolio.owner == result
    assert portfolio in result.portfolios
