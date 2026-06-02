# User Onboarding with Starter Portfolio - Implementation Plan

**Endpoint:** `POST /users/onboard`

---

## 1. Overview

This feature onboards a new user with a starter portfolio in a single atomic database transaction. The endpoint creates a UserProfile, a Portfolio owned by that user, and optionally PortfolioHoldings for initial assets. If any step fails (duplicate email, invalid asset_id, database constraint violation), the entire operation rolls back, ensuring no orphan records exist.

---

## 2. Architecture Decision

The implementation follows the Service Layer pattern to separate business logic from HTTP concerns. The router handles request validation and response formatting, while the service manages database operations. The service uses the existing SQLAlchemy session with `autocommit=False`, ensuring all operations are batched into a single transaction. Dependency Inversion is maintained by injecting the Session into the service, making it testable in isolation.

---

## 3. Implementation Steps

### Step 1: Create Exception Classes

**File:** `app/exceptions/__init__.py` (create directory and file)
**File:** `app/exceptions/business.py`

```python
# app/exceptions/business.py

class BusinessError(Exception):
    """Base class for business logic errors."""
    pass


class InvalidAssetError(BusinessError):
    """Raised when a referenced asset does not exist."""

    def __init__(self, asset_id: int):
        self.asset_id = asset_id
        super().__init__(f"Asset {asset_id} not found")
```

---

### Step 2: Create Pydantic Schemas

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
    portfolio: PortfolioOut

    model_config = {"from_attributes": True}
```

---

### Step 3: Create Onboarding Service

**File:** `app/services/__init__.py` (create directory and file)
**File:** `app/services/onboarding_service.py`

```python
# app/services/onboarding_service.py

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.exceptions.business import InvalidAssetError
from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.models.user_profile import UserProfile
from app.schemas.onboarding import StarterHolding, UserOnboardRequest


class OnboardingService:
    """Service for user onboarding with starter portfolio."""

    def __init__(self, db: Session):
        self.db = db

    def onboard_user(self, request: UserOnboardRequest) -> UserProfile:
        """Create user, portfolio, and holdings atomically.

        Args:
            request: The onboarding request data.

        Returns:
            The created UserProfile with portfolio eagerly loaded.

        Raises:
            InvalidAssetError: If a referenced asset_id does not exist.
            IntegrityError: If email or username already exists.
        """
        # Validate assets exist before creating anything
        if request.starter_holdings:
            self._validate_assets(request.starter_holdings)

        # Create user
        user = UserProfile(
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()

        # Create portfolio
        portfolio = Portfolio(
            owner_id=user.id,
            name=request.portfolio_name,
            description=request.portfolio_description,
        )
        self.db.add(portfolio)
        self.db.flush()

        # Create holdings
        for h in request.starter_holdings:
            holding = PortfolioHolding(
                portfolio_id=portfolio.id,
                asset_id=h.asset_id,
                quantity=h.quantity,
                purchase_price=h.purchase_price,
                purchased_at=datetime.now(timezone.utc),
            )
            self.db.add(holding)

        self.db.commit()
        self.db.refresh(user)
        return user

    def _validate_assets(self, holdings: list[StarterHolding]) -> None:
        """Validate all asset_ids exist."""
        asset_ids = [h.asset_id for h in holdings]
        existing = self.db.query(Asset.id).filter(Asset.id.in_(asset_ids)).all()
        existing_ids = {row[0] for row in existing}

        for asset_id in asset_ids:
            if asset_id not in existing_ids:
                raise InvalidAssetError(asset_id)
```

---

### Step 4: Create Router

**File:** `app/routers/onboarding.py`

```python
# app/routers/onboarding.py

"""User onboarding routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions.business import InvalidAssetError
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
        return UserOnboardResponse.model_validate(user)

    except InvalidAssetError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or username already exists")
```

---

### Step 5: Register Router

**File to modify:** `app/main.py`

```python
from app.routers import onboarding

app.include_router(onboarding.router)
```

---

## 4. Data Flow

1. Request enters router, Pydantic validates input
2. Router instantiates OnboardingService with injected Session
3. Service validates all asset_ids exist (fail-fast)
4. Service creates UserProfile, flushes to get ID
5. Service creates Portfolio with owner_id FK, flushes to get ID
6. Service creates PortfolioHoldings with portfolio_id FK
7. Service commits transaction (all-or-nothing)
8. Router returns response with nested portfolio data

---

## 5. Concerns and Mitigations

**Concern 1: Race condition on duplicate email.**
The database unique constraint is the source of truth. IntegrityError is caught and mapped to HTTP 409.

**Concern 2: Large starter_holdings list.**
Limited to 20 holdings via Pydantic `max_length` constraint.

**Concern 3: Service testability.**
Session injected via constructor; tests can use in-memory SQLite or mock.

**Concern 4: Asset validation performance.**
Single `IN` query for all asset_ids. O(n) where n is holdings count, acceptable for max 20.