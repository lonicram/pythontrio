# Implementation Plan: Asset Price History Feature

## Overview

Design and implement a data model to store asset price updates over time, enabling:
- Tracking current price of each asset
- Recording historical price changes
- Generating price change charts
- Supporting future cron job price updates from external sources

## Prerequisites

- Existing `Asset` model with `price` column (already in place)
- Alembic configured for migrations
- FastAPI with SQLAlchemy setup

## Architecture Decision Records

### ADR-1: Separate PriceHistory Table vs. Only Asset.price

**Decision**: Create a separate `AssetPriceHistory` table while keeping `Asset.price` for current price.

**Rationale**:
- **Performance**: Keep `Asset.price` as denormalized current price to avoid JOIN for common queries
- **History**: Dedicated table optimized for time-series queries (charting)
- **Flexibility**: Can track metadata per price update (source, currency, etc.)

### ADR-2: Price Update Strategy

**Decision**: When recording a new price:
1. Insert into `AssetPriceHistory`
2. Update `Asset.price` with the new value

**Rationale**:
- Single source of truth for current price (fast reads)
- Complete history preserved for analytics
- Atomic operation in service layer

---

## Data Models

### New Model: `AssetPriceHistory`

```
┌─────────────────────────────────────────────────────────────┐
│                    asset_price_history                       │
├─────────────────────────────────────────────────────────────┤
│ id              INTEGER       PRIMARY KEY, AUTO_INCREMENT    │
│ asset_id        INTEGER       FK → assets.id, NOT NULL       │
│ price           DECIMAL(12,2) NOT NULL                       │
│ currency        VARCHAR(3)    DEFAULT 'USD', NOT NULL        │
│ source          VARCHAR(50)   NULL (e.g., 'yahoo', 'manual') │
│ recorded_at     DATETIME      NOT NULL (when price was valid)│
│ created_at      DATETIME      server_default=now()           │
├─────────────────────────────────────────────────────────────┤
│ INDEXES:                                                     │
│   - ix_asset_price_history_asset_recorded                    │
│     (asset_id, recorded_at DESC) - for chart queries         │
│   - ix_asset_price_history_recorded_at                       │
│     (recorded_at) - for batch queries by date                │
└─────────────────────────────────────────────────────────────┘
```

### Relationships

```
Portfolio (1) ────────< (N) Asset (1) ────────< (N) AssetPriceHistory
```

---

## Implementation Steps

### Step 1: Create the AssetPriceHistory Model

**What**: Create a new SQLAlchemy model for price history

**Where**: `/app/models/asset_price_history.py` (new file)

**How**:
```python
"""Asset price history model."""

from sqlalchemy import (
    Column, DateTime, DECIMAL, ForeignKey, Index, Integer, String, func
)
from sqlalchemy.orm import relationship

from app.database import Base


class AssetPriceHistory(Base):
    """Stores historical price records for assets.
    
    Each record represents a price snapshot at a specific point in time.
    Used for tracking price changes and generating price charts.
    """

    __tablename__ = "asset_price_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    price = Column(DECIMAL(precision=12, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    source = Column(String(50), nullable=True)  # e.g., 'yahoo', 'manual', 'cron'
    recorded_at = Column(DateTime, nullable=False)  # When the price was valid
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="price_history")

    # Composite index for efficient chart queries: get prices for an asset ordered by time
    __table_args__ = (
        Index(
            "ix_asset_price_history_asset_recorded",
            "asset_id",
            recorded_at.desc()
        ),
    )
```

**Why**: 
- Separate table allows unlimited historical records without bloating the main Asset table
- `recorded_at` vs `created_at`: `recorded_at` is when the price was actually valid (important for delayed data), `created_at` is when we stored it
- `source` enables tracking where prices come from (useful when multiple cron jobs or manual updates exist)
- `currency` future-proofs for multi-currency support
- Composite index optimizes the most common query: "get price history for asset X ordered by date"

---

### Step 2: Update Asset Model with Relationship

**What**: Add back-reference relationship to Asset model

**Where**: `/app/models/asset.py`

**How**: Add this line inside the `Asset` class:
```python
# Add after the portfolio relationship
price_history = relationship(
    "AssetPriceHistory", 
    back_populates="asset",
    order_by="desc(AssetPriceHistory.recorded_at)"
)
```

**Why**: Enables accessing price history from an asset object: `asset.price_history`

---

### Step 3: Update Models __init__.py

**What**: Export the new model

**Where**: `/app/models/__init__.py`

**How**:
```python
from app.models.asset import Asset
from app.models.asset_price_history import AssetPriceHistory
from app.models.portfolio import Portfolio

__all__ = ["Asset", "AssetPriceHistory", "Portfolio"]
```

**Why**: Ensures Alembic discovers the new model for migration auto-generation

---

### Step 4: Create Pydantic Schemas

**What**: Add request/response schemas for price history

**Where**: `/app/schemas.py` (add to existing file)

**How**:
```python
from datetime import datetime

# --- Asset Price History Schemas ---

class AssetPriceHistoryBase(BaseModel):
    """Base schema for asset price history."""
    
    price: Decimal
    currency: str = "USD"
    source: str | None = None
    recorded_at: datetime


class AssetPriceHistoryCreate(AssetPriceHistoryBase):
    """Schema for recording a new price."""
    
    asset_id: int


class AssetPriceHistoryResponse(AssetPriceHistoryBase):
    """Schema for price history response."""
    
    id: int
    asset_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AssetPriceChartPoint(BaseModel):
    """Simplified schema for chart data points."""
    
    price: Decimal
    recorded_at: datetime


class AssetPriceChartResponse(BaseModel):
    """Schema for chart data response."""
    
    asset_id: int
    asset_name: str
    currency: str
    data_points: list[AssetPriceChartPoint]
```

**Why**: 
- `AssetPriceHistoryCreate` for API input when recording prices
- `AssetPriceChartResponse` provides a clean format for frontend charting libraries
- Separated concerns: full history records vs. lightweight chart data

---

### Step 5: Create Alembic Migration

**What**: Generate and customize migration for the new table

**Where**: `/alembic/versions/` (new migration file)

**How**: 
1. Run: `alembic revision --autogenerate -m "add_asset_price_history"`
2. Review and adjust the generated migration

Expected migration content:
```python
def upgrade() -> None:
    op.create_table(
        'asset_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_price_history_id'), 'asset_price_history', ['id'], unique=False)
    op.create_index(
        'ix_asset_price_history_asset_recorded', 
        'asset_price_history', 
        ['asset_id', sa.text('recorded_at DESC')], 
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_asset_price_history_asset_recorded', table_name='asset_price_history')
    op.drop_index(op.f('ix_asset_price_history_id'), table_name='asset_price_history')
    op.drop_table('asset_price_history')
```

3. Run: `alembic upgrade head`

**Why**: Alembic tracks database schema changes, allowing consistent migrations across environments

---

### Step 6: Add CRUD Operations

**What**: Database operations for price history

**Where**: `/app/crud.py` (add to existing file)

**How**:
```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Asset, AssetPriceHistory


def record_asset_price(
    db: Session,
    asset_id: int,
    price: Decimal,
    recorded_at: datetime,
    currency: str = "USD",
    source: str | None = None,
    update_current_price: bool = True
) -> AssetPriceHistory:
    """Record a new price for an asset.
    
    Args:
        db: Database session.
        asset_id: ID of the asset.
        price: The price value.
        recorded_at: When this price was valid.
        currency: Currency code (default USD).
        source: Source of the price data (e.g., 'yahoo', 'manual').
        update_current_price: If True, also update Asset.price.
    
    Returns:
        The created AssetPriceHistory record.
    """
    price_record = AssetPriceHistory(
        asset_id=asset_id,
        price=price,
        currency=currency,
        source=source,
        recorded_at=recorded_at,
    )
    db.add(price_record)
    
    if update_current_price:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset:
            asset.price = price
    
    db.commit()
    db.refresh(price_record)
    return price_record


def get_asset_price_history(
    db: Session,
    asset_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100
) -> list[AssetPriceHistory]:
    """Get price history for an asset.
    
    Args:
        db: Database session.
        asset_id: ID of the asset.
        start_date: Filter prices after this date.
        end_date: Filter prices before this date.
        limit: Maximum number of records to return.
    
    Returns:
        List of price history records, newest first.
    """
    query = db.query(AssetPriceHistory).filter(
        AssetPriceHistory.asset_id == asset_id
    )
    
    if start_date:
        query = query.filter(AssetPriceHistory.recorded_at >= start_date)
    if end_date:
        query = query.filter(AssetPriceHistory.recorded_at <= end_date)
    
    return query.order_by(
        AssetPriceHistory.recorded_at.desc()
    ).limit(limit).all()


def get_latest_price(db: Session, asset_id: int) -> AssetPriceHistory | None:
    """Get the most recent price record for an asset.
    
    Args:
        db: Database session.
        asset_id: ID of the asset.
    
    Returns:
        The latest price record or None.
    """
    return db.query(AssetPriceHistory).filter(
        AssetPriceHistory.asset_id == asset_id
    ).order_by(
        AssetPriceHistory.recorded_at.desc()
    ).first()
```

**Why**: 
- `record_asset_price` atomically updates both history and Asset.price
- `update_current_price` flag allows flexibility (e.g., backfilling historical data without changing current price)
- Date filtering enables time-range queries for charts

---

### Step 7: Create API Router for Price History

**What**: REST endpoints for price history operations

**Where**: `/app/routers/prices.py` (new file)

**How**:
```python
"""Price history API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.models import Asset
from app.schemas import (
    AssetPriceHistoryCreate,
    AssetPriceHistoryResponse,
    AssetPriceChartResponse,
    AssetPriceChartPoint,
)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/", response_model=AssetPriceHistoryResponse)
def record_price(
    price_data: AssetPriceHistoryCreate,
    db: Session = Depends(get_db)
) -> AssetPriceHistoryResponse:
    """Record a new price for an asset.
    
    This endpoint is designed to be called by:
    - Manual price updates
    - Cron jobs fetching prices from external sources
    """
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == price_data.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    record = crud.record_asset_price(
        db=db,
        asset_id=price_data.asset_id,
        price=price_data.price,
        recorded_at=price_data.recorded_at,
        currency=price_data.currency,
        source=price_data.source,
    )
    return record


@router.get("/assets/{asset_id}/history", response_model=list[AssetPriceHistoryResponse])
def get_price_history(
    asset_id: int,
    start_date: datetime | None = Query(None, description="Filter from this date"),
    end_date: datetime | None = Query(None, description="Filter until this date"),
    limit: int = Query(100, le=1000, description="Max records to return"),
    db: Session = Depends(get_db)
) -> list[AssetPriceHistoryResponse]:
    """Get price history for an asset."""
    return crud.get_asset_price_history(
        db=db,
        asset_id=asset_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


@router.get("/assets/{asset_id}/chart", response_model=AssetPriceChartResponse)
def get_price_chart_data(
    asset_id: int,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db)
) -> AssetPriceChartResponse:
    """Get price data formatted for charting.
    
    Returns data points in chronological order (oldest first)
    suitable for time-series charts.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    history = crud.get_asset_price_history(
        db=db,
        asset_id=asset_id,
        start_date=start_date,
        end_date=end_date,
        limit=1000
    )
    
    # Reverse to chronological order for charting
    data_points = [
        AssetPriceChartPoint(price=h.price, recorded_at=h.recorded_at)
        for h in reversed(history)
    ]
    
    return AssetPriceChartResponse(
        asset_id=asset_id,
        asset_name=asset.name,
        currency=history[0].currency if history else "USD",
        data_points=data_points
    )
```

**Why**:
- `POST /prices/` - Entry point for cron jobs and manual updates
- `GET /prices/assets/{id}/history` - Full history with filtering
- `GET /prices/assets/{id}/chart` - Optimized format for frontend charts

---

### Step 8: Register Router in Main App

**What**: Include the new router in FastAPI app

**Where**: `/app/main.py`

**How**: Add import and include:
```python
from app.routers import prices

app.include_router(prices.router)
```

---

## API Specifications

### POST /prices/
Record a new price for an asset.

**Request Body**:
```json
{
  "asset_id": 1,
  "price": "152.35",
  "currency": "USD",
  "source": "yahoo",
  "recorded_at": "2024-01-15T14:30:00Z"
}
```

**Response** (201):
```json
{
  "id": 42,
  "asset_id": 1,
  "price": "152.35",
  "currency": "USD",
  "source": "yahoo",
  "recorded_at": "2024-01-15T14:30:00Z",
  "created_at": "2024-01-15T14:30:05Z"
}
```

### GET /prices/assets/{asset_id}/chart
Get chart-ready price data.

**Query Parameters**:
- `start_date` (optional): ISO datetime
- `end_date` (optional): ISO datetime

**Response**:
```json
{
  "asset_id": 1,
  "asset_name": "Apple Inc.",
  "currency": "USD",
  "data_points": [
    {"price": "148.50", "recorded_at": "2024-01-10T00:00:00Z"},
    {"price": "150.25", "recorded_at": "2024-01-11T00:00:00Z"},
    {"price": "152.35", "recorded_at": "2024-01-15T00:00:00Z"}
  ]
}
```

---

## Testing Strategy

### Unit Tests
1. **Model tests**: Verify AssetPriceHistory relationships work correctly
2. **CRUD tests**: Test `record_asset_price` updates both history and Asset.price
3. **Edge cases**: Empty history, single record, date filtering

### Integration Tests
1. **API endpoint tests**: Test all three endpoints with valid/invalid data
2. **Database constraints**: Verify foreign key enforcement
3. **Chart data ordering**: Confirm chronological order in response

### Test File Location
`/tests/test_prices.py`

---

## Future Cron Job Considerations

The design supports future cron integration:

```python
# Example cron job usage (for future implementation)
def update_prices_from_yahoo():
    """Cron job to fetch prices from Yahoo Finance."""
    db = SessionLocal()
    try:
        assets = db.query(Asset).all()
        for asset in assets:
            price = fetch_price_from_yahoo(asset.code)
            crud.record_asset_price(
                db=db,
                asset_id=asset.id,
                price=price,
                recorded_at=datetime.utcnow(),
                source="yahoo"
            )
    finally:
        db.close()
```

---

## Rollback Considerations

If issues arise:
1. Run `alembic downgrade -1` to remove the price_history table
2. Remove the new files and relationship additions
3. Remove router registration from main.py

The `Asset.price` column remains unchanged, so existing functionality is preserved.

---

## Summary Checklist

| Step | File | Action |
|------|------|--------|
| 1 | `app/models/asset_price_history.py` | Create new model |
| 2 | `app/models/asset.py` | Add relationship |
| 3 | `app/models/__init__.py` | Export new model |
| 4 | `app/schemas.py` | Add Pydantic schemas |
| 5 | `alembic/versions/xxx_add_asset_price_history.py` | Generate migration |
| 6 | `app/crud.py` | Add CRUD functions |
| 7 | `app/routers/prices.py` | Create API router |
| 8 | `app/main.py` | Register router |
