# app/routers/onboarding.py

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
    """Create user with starter portfolio atomically."""
    service = OnboardingService(db)

    try:
        user = service.onboard_user(request)
        db.commit()
        db.refresh(user)
        return UserOnboardResponse.model_validate(user)

    except IntegrityError as e:
        db.rollback()
        # Distinguish between FK violation (invalid asset) and unique constraint (duplicate email)
        error_msg = str(e.orig).lower()
        if "foreign key" in error_msg or "asset" in error_msg:
            raise HTTPException(status_code=400, detail="Invalid asset_id in holdings")
        raise HTTPException(status_code=409, detail="Email or username already exists")
