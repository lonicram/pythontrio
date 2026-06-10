"""UserProfile API routes for CRUD operations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas import UserProfileResponse

router = APIRouter(prefix="/user-profiles", tags=["user-profiles"])


class UserProfileCreate(BaseModel):
    """Schema for creating a new user profile."""

    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    is_active: bool = True


class UserProfileUpdate(BaseModel):
    """Schema for updating an existing user profile."""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


@router.get("/", response_model=list[UserProfileResponse])
def list_user_profiles(db: Session = Depends(get_db)) -> list[UserProfile]:
    """List all user profiles."""
    return db.query(UserProfile).all()


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_profile(
    user_id: int, db: Session = Depends(get_db)
) -> UserProfile:
    """Get a user profile by ID."""
    user_profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user_profile


@router.post("/", response_model=UserProfileResponse, status_code=201)
def create_user_profile(
    data: UserProfileCreate, db: Session = Depends(get_db)
) -> UserProfile:
    """Create a new user profile."""
    # Check for duplicate email
    existing_email = db.query(UserProfile).filter(
        UserProfile.email == data.email
    ).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")

    # Check for duplicate username if provided
    if data.username:
        existing_username = db.query(UserProfile).filter(
            UserProfile.username == data.username
        ).first()
        if existing_username:
            raise HTTPException(status_code=409, detail="Username already exists")

    user_profile = UserProfile(**data.model_dump())
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)
    return user_profile


@router.put("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(
    user_id: int, data: UserProfileUpdate, db: Session = Depends(get_db)
) -> UserProfile:
    """Update a user profile."""
    user_profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # Check for duplicate email if being changed
    if data.email and data.email != user_profile.email:
        existing_email = db.query(UserProfile).filter(
            UserProfile.email == data.email
        ).first()
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")

    # Check for duplicate username if being changed
    if data.username and data.username != user_profile.username:
        existing_username = db.query(UserProfile).filter(
            UserProfile.username == data.username
        ).first()
        if existing_username:
            raise HTTPException(status_code=409, detail="Username already exists")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user_profile, key, value)

    db.commit()
    db.refresh(user_profile)
    return user_profile


@router.delete("/{user_id}", status_code=204)
def delete_user_profile(user_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a user profile."""
    user_profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    db.delete(user_profile)
    db.commit()