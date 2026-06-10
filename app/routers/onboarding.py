"""User onboarding routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.onboarding import UserOnboardRequest, UserOnboardResponse
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/onboard", response_model=UserOnboardResponse, status_code=201)
def onboard_user(
    request: UserOnboardRequest,
    db: Session = Depends(get_db),
) -> UserOnboardResponse:
    """Create user with starter portfolio atomically.

    Creates a UserProfile, a Portfolio owned by that user, and optionally
    PortfolioHoldings for initial assets. If any step fails, the entire
    operation rolls back, ensuring no orphan records exist.

    Args:
        request: User onboarding request with portfolio and holdings data.
        db: Database session (injected).

    Returns:
        The created user with nested portfolio data.

    Raises:
        HTTPException: 400 if asset_id is invalid, 409 if email/username exists.
    """
    service = OnboardingService(db)

    try:
        user = service.onboard_user(request)
        db.commit()  # Router controls transaction
        db.refresh(user)  # Load relationships
        return UserOnboardResponse.model_validate(user)

    except IntegrityError as e:
        db.rollback()
        # Distinguish between FK violation (invalid asset) and unique constraint
        error_msg = str(e.orig).lower()
        if "foreign key" in error_msg or "asset" in error_msg:
            raise HTTPException(
                status_code=400, detail="Invalid asset_id in holdings"
            )
        raise HTTPException(
            status_code=409, detail="Email or username already exists"
        )