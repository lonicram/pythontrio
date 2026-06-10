"""Service for user onboarding with starter portfolio."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile
from app.schemas.onboarding import UserOnboardRequest


class OnboardingService:
    """Service for user onboarding with starter portfolio."""

    def __init__(self, db: Session):
        """Initialize service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def onboard_user(self, request: UserOnboardRequest) -> UserProfile:
        """Create user, portfolio, and holdings (caller must commit).

        Args:
            request: The onboarding request data.

        Returns:
            The created UserProfile (uncommitted, caller must commit/refresh).

        Note:
            This method does NOT commit. Caller controls transaction boundary.
            IntegrityError may be raised on commit if email/username exists
            or asset_id is invalid.
        """
        # Step 1: Create user (row written to DB via flush)
        user = UserProfile(
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()  # User row now in DB (uncommitted)

        # Step 2: Create portfolio (row written to DB via flush)
        portfolio = Portfolio(
            owner_id=user.id,
            name=request.portfolio_name,
            description=request.portfolio_description,
        )
        self.db.add(portfolio)
        self.db.flush()  # Portfolio row now in DB (uncommitted)

        # Step 3: Create holdings
        # If asset_id is invalid, FK constraint fails on commit
        # This triggers rollback of user AND portfolio
        for h in request.starter_holdings:
            holding = PortfolioHolding(
                portfolio_id=portfolio.id,
                asset_id=h.asset_id,  # No pre-validation - FK will catch it
                quantity=h.quantity,
                purchase_price=h.purchase_price,
                purchased_at=datetime.now(timezone.utc),
            )
            self.db.add(holding)

        # Step 4: Return user (caller controls commit)
        return user