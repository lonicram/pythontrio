"""UserProfile API routes for CRUD operations."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_profile import UserProfile

router = APIRouter(prefix="/user-profiles", tags=["user-profiles"])


class UserProfileCreate(BaseModel):
    """Schema for creating a new user profile.

    Attributes:
        email: Unique email address (required).
        username: Optional unique display name.
        full_name: Optional full name for display.
        is_active: Whether the user account is active (defaults to True).
    """
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    is_active: bool = True


class UserProfileUpdate(BaseModel):
    """Schema for updating an existing user profile.

    All fields are optional to support partial updates.

    Attributes:
        email: Unique email address (optional).
        username: Optional unique display name (optional).
        full_name: Optional full name for display (optional).
        is_active: Whether the user account is active (optional).
    """
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


class UserProfileResponse(BaseModel):
    """Schema for user profile responses.

    Attributes:
        id: Primary key.
        email: Unique email address.
        username: Optional unique display name.
        full_name: Optional full name.
        is_active: Whether the user account is active.
        created_at: Timestamp of profile creation.
        updated_at: Timestamp of last update.
    """
    id: int
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[UserProfileResponse])
def list_user_profiles(db: Session = Depends(get_db)) -> list[UserProfileResponse]:
    """List all user profiles."""
    return db.query(UserProfile).all()


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)) -> UserProfileResponse:
    """Get a user profile by ID.

    Args:
        user_id: The ID of the user profile to retrieve.
        db: Database session dependency.

    Returns:
        The user profile matching the ID.

    Raises:
        HTTPException: 404 if user profile not found.
    """
    user_profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user_profile


@router.post("/", response_model=UserProfileResponse, status_code=201)
def create_user_profile(
    data: UserProfileCreate, db: Session = Depends(get_db)
) -> UserProfileResponse:
    """Create a new user profile.

    Args:
        data: User profile creation data.
        db: Database session dependency.

    Returns:
        The created user profile with assigned ID.

    Raises:
        HTTPException: 409 if email or username already exists.
    """
    # Check for duplicate email
    existing_email = db.query(UserProfile).filter(
        UserProfile.email == data.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    # Check for duplicate username if provided
    if data.username:
        existing_username = db.query(UserProfile).filter(
            UserProfile.username == data.username
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=409,
                detail="Username already exists"
            )

    user_profile = UserProfile(**data.model_dump())
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)
    return user_profile


@router.put("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(
    user_id: int, data: UserProfileUpdate, db: Session = Depends(get_db)
) -> UserProfileResponse:
    """Update a user profile.

    Args:
        user_id: The ID of the user profile to update.
        data: Partial update data (all fields optional).
        db: Database session dependency.

    Returns:
        The updated user profile.

    Raises:
        HTTPException: 404 if user profile not found.
        HTTPException: 409 if email or username already exists.
    """
    user_profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # Check for duplicate email if being changed
    if data.email and data.email != user_profile.email:
        existing_email = db.query(UserProfile).filter(
            UserProfile.email == data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )

    # Check for duplicate username if being changed
    if data.username and data.username != user_profile.username:
        existing_username = db.query(UserProfile).filter(
            UserProfile.username == data.username
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=409,
                detail="Username already exists"
            )

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user_profile, key, value)

    db.commit()
    db.refresh(user_profile)
    return user_profile


@router.delete("/{user_id}", status_code=204)
def delete_user_profile(user_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a user profile.

    Args:
        user_id: The ID of the user profile to delete.
        db: Database session dependency.

    Raises:
        HTTPException: 404 if user profile not found.
    """
    user_profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    db.delete(user_profile)
    db.commit()
