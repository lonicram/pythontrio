# Transaction Patterns Demo - Architecture Plan

## 1. Overview

This plan extends PythonTrio to demonstrate top database transaction patterns used in production systems. The goal is to create educational, demonstrable endpoints that showcase ACID compliance, concurrency handling, and error recovery strategies using SQLAlchemy and PostgreSQL.

## 2. Current State Assessment

### Existing Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| **Asset** | Master catalog of tradeable assets | `id`, `symbol` (unique), `name`, `asset_type`, `price`, timestamps |
| **Portfolio** | User portfolios | `id`, `name`, `description`, timestamps |
| **PortfolioHolding** | Junction table (many-to-many) | `portfolio_id`, `asset_id`, `quantity`, `purchase_price` |
| **AssetPrice** | Historical price time-series | `asset_id`, `price`, `recorded_at`, `source` |

### Existing Relationships
- Portfolio → PortfolioHolding: CASCADE delete
- Asset → PortfolioHolding: RESTRICT delete (protects assets with holdings)
- Asset → AssetPrice: CASCADE delete

### Current Architecture

| Component | Current State | Gap |
|-----------|---------------|-----|
| **Session Management** | `get_db()` dependency with `autocommit=False`, `autoflush=False` | No explicit transaction contexts |
| **Business Logic** | Direct in routers (no service layer) | Need service layer for complex operations |
| **Error Handling** | Basic `HTTPException` (404, 409, 400) | No custom transaction exceptions |
| **Concurrency** | None | No version column, no locking |
| **Database** | SQLite default (configurable) | PostgreSQL needed for isolation demos |

### Existing Router Endpoints

**Assets** (`/assets`): CRUD operations
**Portfolios** (`/portfolios`): CRUD operations
**Holdings** (`/portfolios/{id}/holdings`): Add/update/remove holdings with eager loading
**Asset Prices** (`/assets/{id}/prices`): Append-only price recording with filtering

### What Works Well (Keep)
- Clean Pydantic schemas with `from_attributes=True`
- Proper dependency injection pattern
- Composite key handling in holdings router
- Decimal precision (18,8) for financial data

### What's Missing (Build)
- Service layer for transaction-heavy operations
- Custom exception classes for transaction errors
- `version` column on Asset model for optimistic locking
- Explicit transaction context helpers

---

## 3. Transaction Patterns to Implement

### Pattern 1: Cross-Table Consistency (Atomic Multi-Entity Creation)

**What it demonstrates:** Creating multiple related entities (portfolio + assets) in a single atomic transaction where either everything succeeds or nothing is persisted.

**Use case:** `POST /portfolios/with-assets` endpoint accepts a portfolio definition with a list of assets. The service creates the Portfolio record, then creates each Asset linked to it, committing everything in one transaction. If any asset fails validation (e.g., invalid name), the entire operation rolls back—no orphan portfolios are ever visible in the database.

**Why it matters:** This is the most fundamental transaction pattern. Users often need to create related data together, and partial state (a portfolio without its assets) would violate business invariants. This pattern ensures the database always reflects complete, consistent business objects.

---

### Pattern 2: Unit of Work (Portfolio Rebalancing)

**What it demonstrates:** The Unit of Work pattern tracks all modifications within a transaction and commits them atomically, ensuring all-or-nothing semantics for complex multi-step operations.

**Use case:** `POST /portfolios/{id}/rebalance` accepts target prices for all assets in a portfolio. The service opens an explicit transaction context, updates each asset's price, and only commits when all updates succeed. If updating the third asset fails, the first two updates are rolled back automatically.

**Why it matters:** Rebalancing is a real-world scenario where partial updates are dangerous—you cannot have some assets at new prices while others remain at old prices. The Unit of Work pattern (implemented via SQLAlchemy's Session) guarantees consistency across multiple related changes.

---

### Pattern 3: Savepoints (Bulk Import with Partial Failure Recovery)

**What it demonstrates:** Savepoints create nested transaction boundaries, allowing partial rollbacks while preserving successfully completed work within the same outer transaction.

**Use case:** `POST /assets/prices/bulk-import` accepts hundreds of price records, processes them in batches of 50. Each batch is wrapped in a savepoint via `session.begin_nested()`. If batch #3 contains invalid data, only that batch rolls back to its savepoint—batches #1 and #2 remain committed. The response shows which batches succeeded and which failed.

**Why it matters:** In production systems, bulk operations often encounter partial failures (bad data, constraint violations). Without savepoints, you must either reject the entire import or lose transaction guarantees. Savepoints provide granular recovery, maximizing successful imports while isolating failures.

---

### Pattern 4: Optimistic Locking (Concurrent Price Updates)

**What it demonstrates:** Optimistic locking uses a version column to detect concurrent modifications. When two transactions read the same row, the first to commit wins; the second detects the version mismatch and fails with a conflict error.

**Use case:** Add a `version` column to the Asset model with `__mapper_args__ = {"version_id_col": version}`. When two concurrent requests try to update Bitcoin's price, both read version=5. The first request updates and increments to version=6. The second request attempts to update with version=5, SQLAlchemy raises `StaleDataError`, and the endpoint returns HTTP 409 Conflict with retry guidance.

**Why it matters:** Optimistic locking is the preferred concurrency strategy for high-read, low-write scenarios. It avoids database-level locks that block other transactions, instead detecting conflicts at commit time. This pattern is used extensively in web applications where concurrent edits are possible but rare.

---

### Pattern 5: Explicit Rollback (Asset Transfer with Validation)

**What it demonstrates:** Programmatic rollback handling when business rules fail mid-transaction, showing how to safely abort operations and return the database to its previous state.

**Use case:** `POST /assets/{id}/transfer` moves an asset from one portfolio to another. The service begins a transaction, removes the asset from the source portfolio, then validates that the target portfolio hasn't exceeded its 10-asset limit. If validation fails after the removal, explicit `session.rollback()` is called, the asset stays in its original portfolio, and the endpoint returns HTTP 400 with a clear error message.

**Why it matters:** Not all failures are exceptions—sometimes business logic determines an operation cannot complete. This pattern shows how to handle validation failures gracefully, ensuring the database never enters an inconsistent state even when errors occur mid-operation.

---

### Pattern 6: Pessimistic Locking (Portfolio Valuation Snapshot)

**What it demonstrates:** `SELECT FOR UPDATE` acquires exclusive row-level locks, blocking other transactions from modifying the locked rows until the lock is released.

**Use case:** `GET /portfolios/{id}/valuation-locked` calculates total portfolio value by querying all assets with `.with_for_update()`. While the calculation runs (simulated with a brief delay for demo purposes), any concurrent price update requests block and wait. The response includes the valuation and demonstrates that no prices changed during calculation.

**Why it matters:** Pessimistic locking is essential when you need a guaranteed consistent snapshot for calculations, reports, or read-modify-write cycles. Unlike optimistic locking (which detects conflicts after the fact), pessimistic locking prevents conflicts by blocking concurrent access. The trade-off is reduced throughput due to lock contention.

---

### Pattern 7: Transaction Isolation Levels (Phantom Read Demo)

**What it demonstrates:** Different isolation levels provide different consistency guarantees. READ COMMITTED allows phantom reads (new rows appearing mid-transaction), while SERIALIZABLE prevents them.

**Use case:** Two demo endpoints count assets in a portfolio. `GET /demo/isolation/read-committed` counts assets, waits 3 seconds, counts again using READ COMMITTED isolation. `GET /demo/isolation/serializable` does the same with SERIALIZABLE. During the wait, a helper endpoint `POST /demo/assets` inserts a new asset. With READ COMMITTED, the second count shows the new asset (phantom read). With SERIALIZABLE, both counts are identical.

**Why it matters:** Understanding isolation levels is crucial for database developers. Most applications use READ COMMITTED (PostgreSQL default) for performance, but certain operations (financial reconciliation, inventory checks) require SERIALIZABLE to prevent anomalies. This demo makes the abstract concept tangible and observable.

---

## 4. Implementation Structure

### Files to Create

```
app/
├── services/                        # NEW DIRECTORY
│   ├── __init__.py
│   ├── portfolio_service.py         # Rebalancing, valuation, transfer logic
│   └── bulk_import_service.py       # Savepoint-based batch operations
├── routers/
│   └── transaction_demos.py         # NEW: All demo endpoints
├── exceptions/                      # NEW DIRECTORY
│   ├── __init__.py
│   └── transaction.py               # StaleDataConflict, PortfolioLimitExceeded
└── schemas/
    └── transaction_schemas.py       # NEW: Request/response models for demos
```

### Files to Modify

| File | Change |
|------|--------|
| `app/models/asset.py` | Add `version` column + `__mapper_args__` |
| `app/database.py` | Add transaction context helper (optional) |
| `app/main.py` | Register new `transaction_demos` router |

### Service Layer Design

**portfolio_service.py:**
```python
class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def create_with_holdings(self, data: PortfolioWithHoldings) -> Portfolio:
        """Pattern 1: Cross-table consistency"""

    def rebalance(self, portfolio_id: int, target_prices: dict) -> Portfolio:
        """Pattern 2: Unit of Work"""

    def transfer_holding(self, holding_id: int, target_portfolio_id: int) -> PortfolioHolding:
        """Pattern 5: Explicit rollback on validation failure"""

    def get_valuation_locked(self, portfolio_id: int) -> ValuationResult:
        """Pattern 6: Pessimistic locking with FOR UPDATE"""
```

**bulk_import_service.py:**
```python
class BulkImportService:
    def __init__(self, db: Session):
        self.db = db

    def import_prices(self, records: list[PriceRecord], batch_size: int = 50) -> ImportResult:
        """Pattern 3: Savepoints for partial failure recovery"""
```

### Exception Classes

```python
# app/exceptions/transaction.py

class TransactionError(Exception):
    """Base class for transaction-related errors."""

class StaleDataConflict(TransactionError):
    """Raised when optimistic lock detects concurrent modification."""
    def __init__(self, entity: str, entity_id: int, expected_version: int):
        self.entity = entity
        self.entity_id = entity_id
        self.expected_version = expected_version

class PortfolioLimitExceeded(TransactionError):
    """Raised when portfolio would exceed maximum holdings."""
    def __init__(self, portfolio_id: int, current_count: int, max_count: int = 10):
        self.portfolio_id = portfolio_id
        self.current_count = current_count
        self.max_count = max_count

class TransferValidationError(TransactionError):
    """Raised when asset transfer fails validation."""
```

---

## 5. Model Changes Required

### Asset Model Update (`app/models/asset.py`)

Add version column and mapper configuration for optimistic locking:

```python
# Add to imports
from sqlalchemy.orm import Mapped, mapped_column

# Add to Asset class fields (after updated_at)
version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

# Add mapper args for SQLAlchemy optimistic locking
__mapper_args__ = {
    "version_id_col": version
}
```

**How it works:** SQLAlchemy automatically increments `version` on every UPDATE and includes `WHERE version = :expected` in the UPDATE statement. If no rows match (concurrent modification), `StaleDataError` is raised.

---

## 6. Database Migration Required

**Migration file:** `alembic/versions/xxx_add_asset_version_column.py`

```python
"""Add version column to assets for optimistic locking

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'assets',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1')
    )

def downgrade():
    op.drop_column('assets', 'version')
```

**Run with:** `alembic revision --autogenerate -m "Add asset version column"` then `alembic upgrade head`

---

## 7. Concerns & Mitigations

| Concern | Mitigation |
|---------|------------|
| **PostgreSQL-specific features** | Patterns 6 & 7 require PostgreSQL. Add config check and skip/warn on SQLite. |
| **Demo delays blocking production** | Use `/demo/` prefix; add `ENABLE_DEMO_ENDPOINTS` config flag (default: true in dev) |
| **Deadlocks with pessimistic locking** | Always lock in consistent order (by asset_id ASC); set lock timeout |
| **Optimistic lock retries** | Return `Retry-After: 1` header on 409; document exponential backoff |
| **Isolation level overhead** | SERIALIZABLE for demo only; document 10-30% performance cost |
| **Service layer complexity** | Keep services focused; one pattern per method for clarity |

### Database Compatibility Matrix

| Pattern | SQLite | PostgreSQL | Notes |
|---------|--------|------------|-------|
| Cross-Table Consistency | ✅ | ✅ | Standard ACID |
| Unit of Work | ✅ | ✅ | SQLAlchemy Session |
| Savepoints | ✅ | ✅ | `begin_nested()` works on both |
| Optimistic Locking | ✅ | ✅ | SQLAlchemy `version_id_col` |
| Explicit Rollback | ✅ | ✅ | Standard rollback |
| Pessimistic Locking | ⚠️ | ✅ | SQLite has limited support |
| Isolation Levels | ❌ | ✅ | Requires PostgreSQL |

---

## 8. Recommended Implementation Order

### Phase 1: Foundation (Patterns 1-3)
**Goal:** Establish service layer and basic transaction patterns

1. **Setup** - Create `services/`, `exceptions/` directories and base files
2. **Cross-Table Consistency** - Implement `PortfolioService.create_with_holdings()`
3. **Unit of Work** - Implement `PortfolioService.rebalance()`
4. **Explicit Rollback** - Implement `PortfolioService.transfer_holding()`

### Phase 2: Concurrency (Pattern 4)
**Goal:** Add optimistic locking support

5. **Migration** - Add `version` column to assets table
6. **Model Update** - Add `__mapper_args__` to Asset model
7. **Optimistic Locking** - Add concurrent-safe price update endpoint

### Phase 3: Advanced (Patterns 5-7)
**Goal:** Demonstrate production-grade patterns

8. **Savepoints** - Implement `BulkImportService.import_prices()`
9. **Pessimistic Locking** - Implement `PortfolioService.get_valuation_locked()`
10. **Isolation Levels** - Add demo endpoints (PostgreSQL only)

---

## 9. API Endpoints Summary

All new endpoints go in `app/routers/transaction_demos.py` with prefix `/tx-demo`.

| Endpoint | Pattern | Request Body | Response |
|----------|---------|--------------|----------|
| `POST /tx-demo/portfolios/with-holdings` | Cross-Table | `{name, holdings: [{asset_id, quantity}]}` | Portfolio with holdings |
| `POST /tx-demo/portfolios/{id}/rebalance` | Unit of Work | `{prices: {asset_id: price}}` | Updated portfolio |
| `POST /tx-demo/holdings/{id}/transfer` | Explicit Rollback | `{target_portfolio_id}` | Transferred holding |
| `PUT /tx-demo/assets/{id}/price` | Optimistic Lock | `{price, expected_version}` | Asset or 409 Conflict |
| `POST /tx-demo/prices/bulk-import` | Savepoints | `{records: [{asset_id, price}]}` | Import result with batch status |
| `GET /tx-demo/portfolios/{id}/valuation` | Pessimistic Lock | - | `{total_value, locked_at}` |
| `GET /tx-demo/isolation/read-committed` | Isolation Level | - | Phantom read demo result |
| `GET /tx-demo/isolation/serializable` | Isolation Level | - | Serializable demo result |

### Response Schemas

```python
# Bulk import result (Pattern 3)
class BatchResult(BaseModel):
    batch_number: int
    success: bool
    records_processed: int
    error: str | None = None

class ImportResult(BaseModel):
    total_records: int
    successful_records: int
    failed_batches: list[BatchResult]

# Valuation result (Pattern 6)
class ValuationResult(BaseModel):
    portfolio_id: int
    total_value: Decimal
    holdings_count: int
    calculated_at: datetime
    lock_held_ms: int  # Demo: shows how long lock was held
```