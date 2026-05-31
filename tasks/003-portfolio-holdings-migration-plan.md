# Portfolio Holdings Migration Plan

## 1. Overview

This plan refactors the Portfolio-Asset relationship from a simple one-to-many design to a proper many-to-many relationship using a `PortfolioHolding` junction table. This enables a master asset catalog where each asset (Bitcoin, AAPL) exists once with a single price, while portfolios track their holdings with quantities and purchase prices.

## 2. Current vs Target Architecture

### Current Design (Problematic)

```
Portfolio (1) ────────► (N) Asset ────────► (N) AssetPrice
                            │
                            ├── portfolio_id (FK)
                            ├── name ("Bitcoin")
                            ├── price (duplicated per portfolio)
                            └── description
```

**Issues:** Asset data duplicated across portfolios, price sync updates multiple records, no master asset catalog.

### Target Design (Recommended)

```
Portfolio (1) ◄──► (N) PortfolioHolding (N) ◄──► (1) Asset ──► (N) AssetPrice
                        │                            │
                        ├── quantity                 ├── symbol (unique)
                        ├── purchase_price           ├── name
                        └── purchased_at             ├── asset_type
                                                     └── price (single source)
```

**Benefits:** Single source of truth for prices, master asset catalog, rich holding metadata, cleaner queries.

---

## 3. Migration Strategy

We use an **expand-contract migration** pattern to ensure zero downtime and safe rollback:

1. **Expand Phase:** Add new tables/columns alongside existing ones
2. **Migrate Phase:** Copy and transform data
3. **Contract Phase:** Remove old columns/tables

---

## 4. Implementation Steps

### Step 1: Create New Models (Code Only)

Create new model files without running migrations yet.

**File: `app/models/portfolio_holding.py`**

```python
"""PortfolioHolding model - junction table for Portfolio-Asset relationship."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PortfolioHolding(Base):
    """Represents an asset holding within a portfolio.

    This junction table enables many-to-many relationship between
    portfolios and assets, with additional metadata like quantity
    and purchase price for P&L calculations.
    """

    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),  # Don't delete assets with holdings
        nullable=False
    )

    # Holding details
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        default=Decimal("0")
    )
    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Price per unit when acquired"
    )
    purchased_at: Mapped[datetime | None] = mapped_column(nullable=True)

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
    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship(back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", name="uq_portfolio_holding"),
        Index("ix_holdings_portfolio_id", "portfolio_id"),
        Index("ix_holdings_asset_id", "asset_id"),
    )

    def __repr__(self) -> str:
        return f"<PortfolioHolding(portfolio={self.portfolio_id}, asset={self.asset_id}, qty={self.quantity})>"
```

---

### Step 2: Update Asset Model

Modify Asset to become a master catalog entity.

**File: `app/models/asset.py` (updated)**

```python
"""Asset model - master catalog of tradeable assets."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    """Master asset definition (e.g., Bitcoin, AAPL).

    Each asset exists once in the system with a single current price.
    Portfolios reference assets through PortfolioHolding.
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique ticker symbol (BTC, AAPL)"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name (Bitcoin, Apple Inc.)"
    )
    asset_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="crypto",
        comment="Asset category: crypto, stock, etf, commodity"
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Current market price (single source of truth)"
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
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    prices: Mapped[list["AssetPrice"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(symbol={self.symbol}, name={self.name}, price={self.price})>"
```

---

### Step 3: Update Portfolio Model

**File: `app/models/portfolio.py` (updated)**

```python
"""Portfolio model with holdings relationship."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Portfolio(Base):
    """User portfolio containing asset holdings."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan"
    )

    @property
    def total_value(self) -> Decimal:
        """Calculate total portfolio value from holdings."""
        return sum(
            (h.quantity * h.asset.price)
            for h in self.holdings
            if h.asset.price is not None
        )

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name={self.name})>"
```

---

### Step 4: Update Models `__init__.py`

**File: `app/models/__init__.py`**

```python
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding

__all__ = ["Asset", "AssetPrice", "Portfolio", "PortfolioHolding"]
```

---

### Step 5: Alembic Migration (Expand Phase)

Create migration that adds new structure while preserving old data.

```bash
alembic revision -m "add_portfolio_holdings_refactor"
```

**Migration file:**

```python
"""add_portfolio_holdings_refactor

Revision ID: xxxx
Revises: f3948fcdff53
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "xxxx"
down_revision = "f3948fcdff53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns to assets table
    op.add_column("assets", sa.Column("symbol", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("asset_type", sa.String(20), nullable=True, server_default="crypto"))
    op.add_column("assets", sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()))
    op.add_column("assets", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # 2. Add timestamps to portfolios
    op.add_column("portfolios", sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()))
    op.add_column("portfolios", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # 3. Create portfolio_holdings table
    op.create_table(
        "portfolio_holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("purchase_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("portfolio_id", "asset_id", name="uq_portfolio_holding"),
    )
    op.create_index("ix_holdings_portfolio_id", "portfolio_holdings", ["portfolio_id"])
    op.create_index("ix_holdings_asset_id", "portfolio_holdings", ["asset_id"])

    # 4. Migrate data: populate symbol from name, create holdings from existing assets
    op.execute("""
        UPDATE assets
        SET symbol = UPPER(REPLACE(REPLACE(name, ' ', ''), '.', ''))
        WHERE symbol IS NULL
    """)

    # 5. Create holdings from existing portfolio-asset relationships
    op.execute("""
        INSERT INTO portfolio_holdings (portfolio_id, asset_id, quantity, created_at)
        SELECT portfolio_id, id, 1.0, NOW()
        FROM assets
        WHERE portfolio_id IS NOT NULL
    """)

    # 6. Make symbol required and unique (after data migration)
    op.alter_column("assets", "symbol", nullable=False)
    op.create_unique_constraint("uq_asset_symbol", "assets", ["symbol"])
    op.create_index("ix_asset_symbol", "assets", ["symbol"])

    # 7. Change price column from Float to Numeric
    op.alter_column(
        "assets",
        "price",
        type_=sa.Numeric(18, 8),
        existing_type=sa.Float(),
        existing_nullable=True
    )


def downgrade() -> None:
    # Reverse in opposite order
    op.alter_column("assets", "price", type_=sa.Float(), existing_type=sa.Numeric(18, 8))
    op.drop_index("ix_asset_symbol", "assets")
    op.drop_constraint("uq_asset_symbol", "assets")
    op.drop_index("ix_holdings_asset_id", "portfolio_holdings")
    op.drop_index("ix_holdings_portfolio_id", "portfolio_holdings")
    op.drop_table("portfolio_holdings")
    op.drop_column("portfolios", "updated_at")
    op.drop_column("portfolios", "created_at")
    op.drop_column("assets", "updated_at")
    op.drop_column("assets", "created_at")
    op.drop_column("assets", "asset_type")
    op.drop_column("assets", "symbol")
```

---

### Step 6: Second Migration (Contract Phase)

After verifying data integrity, remove old `portfolio_id` from assets.

```bash
alembic revision -m "remove_asset_portfolio_fk"
```

```python
"""remove_asset_portfolio_fk

Revision ID: yyyy
Revises: xxxx
"""

def upgrade() -> None:
    # Remove old foreign key and column
    op.drop_constraint("assets_portfolio_id_fkey", "assets", type_="foreignkey")
    op.drop_column("assets", "portfolio_id")


def downgrade() -> None:
    op.add_column("assets", sa.Column("portfolio_id", sa.Integer(), nullable=True))
    op.create_foreign_key("assets_portfolio_id_fkey", "assets", "portfolios", ["portfolio_id"], ["id"])
```

---

## 5. Data Migration Details

### Before Migration

| assets table |||||
|---|---|---|---|---|
| id | name | portfolio_id | price | description |
| 1 | Bitcoin | 1 | 67000 | Crypto |
| 2 | Bitcoin | 2 | 67000 | Crypto |
| 3 | AAPL | 1 | 189.5 | Apple |

### After Migration

| assets table ||||||
|---|---|---|---|---|---|
| id | symbol | name | asset_type | price | description |
| 1 | BTC | Bitcoin | crypto | 67000 | Crypto |
| 2 | AAPL | Apple | stock | 189.5 | Apple |

| portfolio_holdings table |||||
|---|---|---|---|---|
| id | portfolio_id | asset_id | quantity | purchase_price |
| 1 | 1 | 1 | 1.0 | NULL |
| 2 | 2 | 1 | 1.0 | NULL |
| 3 | 1 | 2 | 1.0 | NULL |

**Note:** Duplicate assets (two "Bitcoin" records) need deduplication logic. The migration should:
1. Find unique assets by name
2. Keep one, update holdings to reference it
3. Delete duplicates

---

## 6. Deduplication Logic

Add this to the migration before creating holdings:

```python
# Deduplicate assets by name, keeping lowest ID
op.execute("""
    WITH duplicates AS (
        SELECT name, MIN(id) as keep_id
        FROM assets
        GROUP BY name
    ),
    to_update AS (
        SELECT a.id as old_id, d.keep_id as new_id
        FROM assets a
        JOIN duplicates d ON a.name = d.name
        WHERE a.id != d.keep_id
    )
    -- First, update asset_prices to point to canonical asset
    UPDATE asset_prices
    SET asset_id = to_update.new_id
    FROM to_update
    WHERE asset_prices.asset_id = to_update.old_id
""")

op.execute("""
    WITH duplicates AS (
        SELECT name, MIN(id) as keep_id
        FROM assets
        GROUP BY name
    )
    -- Delete duplicate asset records
    DELETE FROM assets
    WHERE id NOT IN (SELECT keep_id FROM duplicates)
""")
```

---

## 7. API Changes Required

### New Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /assets` | List all available assets (master catalog) |
| `POST /assets` | Create new asset in catalog |
| `GET /portfolios/{id}/holdings` | List holdings with asset details |
| `POST /portfolios/{id}/holdings` | Add asset to portfolio |
| `PUT /portfolios/{id}/holdings/{asset_id}` | Update holding quantity |
| `DELETE /portfolios/{id}/holdings/{asset_id}` | Remove asset from portfolio |

### Updated Price Sync Script

```python
# Old: Update each asset copy
for asset in assets:
    api.submit_price(asset_id=asset["id"], price=price)

# New: Update single canonical asset
asset = api.get_asset_by_symbol("BTC")
api.submit_price(asset_id=asset["id"], price=price)
```

---

## 8. Testing Checklist

- [ ] Migration runs successfully on empty database
- [ ] Migration runs successfully on database with existing data
- [ ] Duplicate assets are properly deduplicated
- [ ] Holdings are created for all existing portfolio-asset relationships
- [ ] Asset prices are preserved
- [ ] AssetPrice foreign keys still work
- [ ] Rollback (downgrade) works correctly
- [ ] API endpoints return expected data
- [ ] Price sync script works with new structure

---

## 9. Rollback Plan

If issues occur after deployment:

1. **Immediate:** Run `alembic downgrade -1` to restore `portfolio_id` column
2. **Data:** Holdings table data maps back to direct relationships
3. **Code:** Revert model changes via git

---

## 10. Execution Order

| Step | Action | Reversible |
|------|--------|------------|
| 1 | Create new model files | Yes (git) |
| 2 | Run expand migration | Yes (alembic) |
| 3 | Verify data integrity | N/A |
| 4 | Update API endpoints | Yes (git) |
| 5 | Update price sync script | Yes (git) |
| 6 | Run contract migration | Yes (alembic) |
| 7 | Remove old model code | Yes (git) |