# User Onboarding with Starter Portfolio - Implementation Plan

**Endpoint:** `POST /users/onboard`

---

## 1. Overview

This feature onboards a new user with a starter portfolio in a single atomic database transaction. The endpoint creates a UserProfile, a Portfolio owned by that user, and optionally PortfolioHoldings for initial assets. If any step fails, the entire operation rolls back, ensuring no orphan records exist.

**Why transactions matter here:** We intentionally defer asset validation to the database FK constraint. This means if a holding references an invalid `asset_id`, the user and portfolio rows are already written (via `flush()`) and must be rolled back. This makes the atomic behavior observable and testable.

---

## 2. Architecture Decision

The implementation follows the Service Layer pattern to separate business logic from HTTP concerns. The router handles request validation and response formatting, while the service manages database operations. The service uses the existing SQLAlchemy session with `autocommit=False`, ensuring all operations are batched into a single transaction. Dependency Inversion is maintained by injecting the Session into the service, making it testable in isolation.

---

## 3. Implementation Steps

### Step 1: Create Pydantic Schemas

**File:** `app/schemas/__init__.py` (create directory and file)
**File:** `app/schemas/onboarding.py`

```python
# app/schemas/onboarding.py

from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class StarterHolding(BaseModel):
    """A holding to add to the starter portfolio."""
    asset_id: int
    quantity: Decimal = Field(..., gt=0)
    purchase_price: Decimal | None = None


class UserOnboardRequest(BaseModel):
    """Request for user onboarding with starter portfolio."""
    email: EmailStr
    username: str | None = Field(None, max_length=50)
    full_name: str | None = Field(None, max_length=100)
    portfolio_name: str = Field(default="My Portfolio", max_length=100)
    portfolio_description: str | None = Field(None, max_length=500)
    starter_holdings: list[StarterHolding] = Field(default_factory=list, max_length=20)


class HoldingOut(BaseModel):
    """Response schema for a portfolio holding."""
    asset_id: int
    quantity: Decimal
    purchase_price: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    """Response schema for a portfolio."""
    id: int
    name: str
    description: str | None
    holdings: list[HoldingOut]

    model_config = {"from_attributes": True}


class UserOnboardResponse(BaseModel):
    """Response for successful user onboarding."""
    id: int
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    portfolios: list[PortfolioOut]  # Matches UserProfile.portfolios relationship

    model_config = {"from_attributes": True}
```

---

### Step 2: Create Onboarding Service

**File:** `app/services/__init__.py` (create directory and file)
**File:** `app/services/onboarding_service.py`

```python
# app/services/onboarding_service.py

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile
from app.schemas.onboarding import UserOnboardRequest


class OnboardingService:
    """Service for user onboarding with starter portfolio."""

    def __init__(self, db: Session):
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
```

---

### Step 3: Create Router

**File:** `app/routers/onboarding.py`

```python
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
        db.commit()       # Router controls transaction
        db.refresh(user)  # Load relationships
        return UserOnboardResponse.model_validate(user)

    except IntegrityError as e:
        db.rollback()
        # Distinguish between FK violation (invalid asset) and unique constraint (duplicate email)
        error_msg = str(e.orig).lower()
        if "foreign key" in error_msg or "asset" in error_msg:
            raise HTTPException(status_code=400, detail="Invalid asset_id in holdings")
        raise HTTPException(status_code=409, detail="Email or username already exists")
```

---

### Step 4: Register Router

**File to modify:** `app/main.py`

```python
from app.routers import onboarding

app.include_router(onboarding.router)
```

---

## 4. Data Flow

1. Request enters router, Pydantic validates input
2. Router instantiates OnboardingService with injected Session
3. Service creates UserProfile, flushes to get ID
4. Service creates Portfolio with owner_id FK, flushes to get ID
5. Service creates PortfolioHoldings with portfolio_id FK
6. Service returns user (no commit)
7. Router commits transaction (all-or-nothing)
8. Router refreshes user to load relationships
9. Router returns response with nested portfolio data

---

## 5. Concerns and Mitigations

**Concern 1: Race condition on duplicate email.**
The database unique constraint is the source of truth. IntegrityError is caught and mapped to HTTP 409.

**Concern 2: Large starter_holdings list.**
Limited to 20 holdings via Pydantic `max_length` constraint.

**Concern 3: Service testability.**
Session injected via constructor; tests can use in-memory SQLite or mock.

**Concern 4: Error message quality for FK violations.**
The IntegrityError message varies by database. The router checks for "foreign key" or "asset" in the error string. For production, consider database-specific error parsing or pre-validation.

---

## 6. Optional Enhancements (Future)

### Enhancement A: Pre-validation for Better Error Messages

If clearer error messages are needed (e.g., "Asset 999 not found"), add pre-validation:

```python
def _validate_assets(self, holdings: list[StarterHolding]) -> None:
    """Validate all asset_ids exist before creating records."""
    asset_ids = [h.asset_id for h in holdings]
    existing = self.db.query(Asset.id).filter(Asset.id.in_(asset_ids)).all()
    existing_ids = {row[0] for row in existing}

    missing = [aid for aid in asset_ids if aid not in existing_ids]
    if missing:
        raise InvalidAssetError(missing)
```

Note: This still demonstrates transactions because the validation happens AFTER `flush()` calls in more complex scenarios.

### Enhancement B: Business Rule Validation Mid-Transaction

Add a portfolio limit check that requires database state and triggers rollback:

```python
def onboard_user(self, request: UserOnboardRequest) -> UserProfile:
    user = UserProfile(...)
    self.db.add(user)
    self.db.flush()  # User row written

    # Business rule: max 5 portfolios per user
    existing_count = self.db.query(Portfolio).filter_by(owner_id=user.id).count()
    if existing_count >= 5:
        self.db.rollback()  # Rollback the user we just created
        raise PortfolioLimitExceeded(user_id=user.id, limit=5)

    portfolio = Portfolio(owner_id=user.id, ...)
    # ... continue
```

This pattern is useful when:
- Validation depends on current database state
- The check must happen after some records are written
- You need to enforce limits that can't be expressed as DB constraints