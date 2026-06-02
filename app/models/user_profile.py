"""UserProfile model for authentication and portfolio ownership."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class UserProfile(Base):
    """User profile for authentication and portfolio ownership.

    Attributes:
        id: Primary key.
        email: Unique email address (required for auth).
        username: Optional unique display name.
        full_name: Optional full name for display.
        is_active: Whether the user can log in.
        created_at: Timestamp of user profile creation.
        updated_at: Timestamp of last update.
        portfolios: User's owned portfolios.
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique email address for authentication"
    )
    username: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        comment="Optional unique display name"
    )
    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User's full name for display"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Whether user account is active"
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    portfolios: Mapped[list["Portfolio"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, email={self.email}, username={self.username})>"