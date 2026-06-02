# User Profile Model Implementation Plan

## 1. Overview

This plan introduces a UserProfile model to support future authentication and authorization capabilities. The UserProfile model will serve as the owner entity for portfolios, enabling multi-user support while maintaining backward compatibility with existing portfolio data. The implementation follows the established SQLAlchemy 2.0+ patterns already present in the codebase, including `Mapped[]` type hints, audit timestamps, and bidirectional relationships with `back_populates`.

## 2. Architecture Decision

The UserProfile model follows the **Single Responsibility Principle** by containing only identity and status fields, delegating authentication concerns (password hashing, tokens) to future auth modules. The nullable `owner_id` foreign key on Portfolio supports **Open-Closed Principle** - existing functionality remains unchanged while new ownership features are added. The bidirectional relationship with cascade delete ensures referential integrity without orphaned portfolios when user profiles are removed.

---

## 3. Implementation Steps

### Step 1: Create UserProfile Model

**File:** `/home/gft_demo/alembic_demo_live/python_trio/app/models/user_profile.py`

```python
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
```

### Step 2: Modify Portfolio Model

**File:** `/home/gft_demo/alembic_demo_live/python_trio/app/models/portfolio.py`

**Add import** for ForeignKey:
```python
from sqlalchemy import ForeignKey, String, func  # Add ForeignKey
```

**Add import** in TYPE_CHECKING block:
```python
if TYPE_CHECKING:
    from app.models.portfolio_holding import PortfolioHolding
    from app.models.user_profile import UserProfile  # Add this line
```

**Add owner_id column** after the `id` field:
```python
id: Mapped[int] = mapped_column(primary_key=True)
owner_id: Mapped[int | None] = mapped_column(
    ForeignKey("user_profiles.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
    comment="Optional user profile who owns this portfolio"
)
```

**Add owner relationship** in the Relationships section:
```python
# Relationships
owner: Mapped["UserProfile | None"] = relationship(back_populates="portfolios")
holdings: Mapped[list["PortfolioHolding"]] = relationship(
    back_populates="portfolio",
    cascade="all, delete-orphan"
)
```

### Step 3: Update Model Exports

**File:** `/home/gft_demo/alembic_demo_live/python_trio/app/models/__init__.py`

```python
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile

__all__ = ["Asset", "AssetPrice", "Portfolio", "PortfolioHolding", "UserProfile"]
```

### Step 4: Create Alembic Migration

Generate migration with:
```bash
cd /home/gft_demo/alembic_demo_live/python_trio
alembic revision --autogenerate -m "add_user_profile_model_and_portfolio_owner"
```

Then review and adjust the generated migration to ensure:

```python
def upgrade() -> None:
    """Add user_profiles table and owner_id to portfolios."""
    # 1. Create user_profiles table
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=True),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"], unique=True)
    op.create_index("ix_user_profiles_username", "user_profiles", ["username"], unique=True)

    # 2. Add owner_id to portfolios (nullable to preserve existing data)
    op.add_column(
        "portfolios",
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=True
        )
    )
    op.create_index("ix_portfolios_owner_id", "portfolios", ["owner_id"])


def downgrade() -> None:
    """Remove user_profiles table and owner_id from portfolios."""
    op.drop_index("ix_portfolios_owner_id", "portfolios")
    op.drop_column("portfolios", "owner_id")
    op.drop_index("ix_user_profiles_username", "user_profiles")
    op.drop_index("ix_user_profiles_email", "user_profiles")
    op.drop_table("user_profiles")
```

### Step 5: Add Unit Tests

Append to `/home/gft_demo/alembic_demo_live/python_trio/tests/unit/test_models.py`:

```python
from app.models.user_profile import UserProfile


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


def test_user_profile_creation_minimal() -> None:
    """Test UserProfile model with only required fields."""
    user_profile = UserProfile(email="minimal@example.com")

    assert user_profile.email == "minimal@example.com"
    assert user_profile.username is None
    assert user_profile.full_name is None
    assert user_profile.is_active is True  # Default


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
```

---

## 4. Data Flow

The UserProfile model sits at the top of the ownership hierarchy: UserProfile -> Portfolio -> PortfolioHolding -> Asset. When a user profile is created, they can create portfolios with `owner_id` pointing to their `user_profiles.id`. The nullable FK ensures existing portfolios without owners continue to function. The `cascade="all, delete-orphan"` on UserProfile.portfolios ensures that when a user profile is deleted, all their portfolios (and transitively, their holdings via Portfolio's own cascade) are cleaned up. The `ondelete="CASCADE"` on the FK ensures database-level enforcement.

---

## 5. Concerns and Mitigations

**Concern 1: Existing portfolios have no owner** - Mitigated by making `owner_id` nullable. Future migration can assign orphan portfolios to a system user profile or prompt for ownership assignment.

**Concern 2: Email uniqueness constraint on existing data** - Not applicable since this is a new table. However, the migration must create indexes after table creation to avoid issues.

**Concern 3: Authentication fields (password_hash, tokens) are missing** - Intentionally deferred. The UserProfile model is designed for extension; password hashing should be added via a separate module (e.g., `passlib`) when auth is implemented, following Interface Segregation.

**Concern 4: Test fixture updates** - Add `sample_user_profile` fixture to `conftest.py` for consistency with existing patterns. Update `sample_portfolio` to optionally accept an owner.

---

## 6. Files to Create/Modify

| File | Action |
|------|--------|
| `app/models/user_profile.py` | Create |
| `app/models/portfolio.py` | Modify (add owner_id, relationship) |
| `app/models/__init__.py` | Modify (export UserProfile) |
| `alembic/versions/XXX_add_user_profile_model_and_portfolio_owner.py` | Create via autogenerate |
| `tests/unit/test_models.py` | Modify (add UserProfile tests) |
| `tests/conftest.py` | Modify (add sample_user_profile fixture) |

---

## 7. Verification Steps

1. [ ] Create `app/models/user_profile.py` with UserProfile class
2. [ ] Update `app/models/portfolio.py` with owner_id and relationship
3. [ ] Update `app/models/__init__.py` exports
4. [ ] Run `alembic revision --autogenerate -m "add_user_profile_model_and_portfolio_owner"`
5. [ ] Review and adjust generated migration
6. [ ] Run `alembic upgrade head` to apply migration
7. [ ] Add UserProfile tests to `tests/unit/test_models.py`
8. [ ] Add `sample_user_profile` fixture to `tests/conftest.py`
9. [ ] Run `pytest` to verify all tests pass
10. [ ] Run `mypy app/models/` to verify type hints
11. [ ] Run `ruff check app/models/` to verify code style