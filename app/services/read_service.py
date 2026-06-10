"""Read-only service for querying portfolio data."""

from sqlalchemy.orm import Session, joinedload

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.user_profile import UserProfile


class ReadService:
    """Service for read-only database queries.

    Following project conventions:
    - Session is injected via constructor
    - No commits (caller controls transaction, though reads don't require it)
    - Returns ORM models; caller handles serialization
    """

    def __init__(self, db: Session):
        """Initialize with database session.

        Args:
            db: SQLAlchemy session for database queries.
        """
        self.db = db

    def list_assets(self) -> list[Asset]:
        """Retrieve all assets.

        Returns:
            List of Asset models ordered by symbol.
        """
        return self.db.query(Asset).order_by(Asset.symbol).all()

    def list_portfolios(self, include_holdings: bool = False) -> list[Portfolio]:
        """Retrieve all portfolios.

        Args:
            include_holdings: If True, eagerly load holdings relationship.

        Returns:
            List of Portfolio models ordered by name.
        """
        query = self.db.query(Portfolio)
        if include_holdings:
            query = query.options(joinedload(Portfolio.holdings))
        return query.order_by(Portfolio.name).all()

    def list_users(self, active_only: bool = True) -> list[UserProfile]:
        """Retrieve user profiles.

        Args:
            active_only: If True, only return active users.

        Returns:
            List of UserProfile models ordered by email.
        """
        query = self.db.query(UserProfile)
        if active_only:
            query = query.filter(UserProfile.is_active == True)  # noqa: E712
        return query.order_by(UserProfile.email).all()