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

### Pattern 4: Optimistic Locking (Concurrent Lifecycle Transitions)

**What it demonstrates:** Optimistic locking uses a version column to detect concurrent modifications to the same row. The pattern shines on **read-validate-write** operations — where the legality of a write depends on the current state — because last-write-wins is provably wrong in that case. Two concurrent `UserProfile` lifecycle transitions illustrate this: one admin deletes a profile while another verifies it. Without optimistic locking the delete is silently overwritten and a deleted account is resurrected into `verified` — an illegal state the transition table explicitly forbids.

**Use case:** Add a `status` state-machine column and a `version` column to `UserProfile`. The state machine has four states (`new`, `verified`, `suspended`, `deleted`) where `deleted` is terminal. The `ALLOWED_TRANSITIONS` dict encodes the legal moves; `__mapper_args__ = {"version_id_col": version}` enforces them concurrently. When two admins both read `status=new, version=1` and one deletes (bumping to `version=2`) before the other verifies, the verifier's `UPDATE … WHERE version=1` matches zero rows, SQLAlchemy raises `StaleDataError`, and the endpoint returns **HTTP 409 Conflict**. The client reloads, sees `status=deleted`, retries the verify, hits the transition-table check, and gets **HTTP 400 Bad Request** ("cannot transition `deleted → verified`"). The demo is driven by two browser tabs acting as two admins; the 409 is deterministic — just don't reload Tab B.

**Why it matters:** The 409-then-400 sequence teaches two distinct failure modes in one interaction: the version check defends data integrity (race); the re-evaluated state machine defends the business invariant (you cannot resurrect a deleted account). Optimistic locking is the preferred concurrency strategy for high-read/low-write scenarios because it avoids database-level locks on the happy path and scales across multiple app servers — the guarantee lives in the DB row, not app memory.

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
│   ├── bulk_import_service.py       # Savepoint-based batch operations
│   └── profile_lifecycle_service.py # Pattern 4: state-machine + optimistic locking
├── routers/
│   └── transaction_demos.py         # NEW: All demo endpoints
├── exceptions/                      # NEW DIRECTORY
│   ├── __init__.py
│   └── transaction.py               # StaleDataConflict, IllegalTransitionError, PortfolioLimitExceeded
└── schemas/
    └── transaction_schemas.py       # NEW: Request/response models for demos
```

### Files to Modify

| File | Change |
|------|--------|
| `app/models/user_profile.py` | Add `ProfileStatus` enum, `status` column, `version` column + `__mapper_args__` |
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

**profile_lifecycle_service.py** (Pattern 4 — mirrors `OnboardingService` "service builds, caller commits" style):
```python
ALLOWED_TRANSITIONS: dict[ProfileStatus, set[ProfileStatus]] = {
    ProfileStatus.NEW:       {ProfileStatus.VERIFIED, ProfileStatus.DELETED},
    ProfileStatus.VERIFIED:  {ProfileStatus.SUSPENDED, ProfileStatus.DELETED},
    ProfileStatus.SUSPENDED: {ProfileStatus.VERIFIED, ProfileStatus.DELETED},
    ProfileStatus.DELETED:   set(),    # terminal: no outbound transitions
}

class ProfileLifecycleService:
    def __init__(self, db: Session):
        self.db = db

    def transition(self, profile_id: int, target: ProfileStatus) -> UserProfile:
        profile = self.db.get(UserProfile, profile_id)
        if profile is None:
            raise ProfileNotFound(profile_id)
        if target not in ALLOWED_TRANSITIONS[profile.status]:
            raise IllegalTransitionError(profile_id, profile.status, target)
        self._run_side_effects(profile, target)
        profile.status = target
        # caller commits; version_id_col enforces expected_version at flush
        return profile
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

class IllegalTransitionError(TransactionError):
    """Raised when a requested lifecycle transition is not permitted by the state machine."""
    def __init__(self, profile_id: int, current_status: ProfileStatus, requested_status: ProfileStatus):
        self.profile_id = profile_id
        self.current_status = current_status
        self.requested_status = requested_status

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

### UserProfile Model Update (`app/models/user_profile.py`)

Add a `ProfileStatus` enum, a `status` state-machine column, and a `version` column for optimistic locking:

```python
import enum
from sqlalchemy import Enum as SAEnum, Integer

class ProfileStatus(str, enum.Enum):
    NEW = "new"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    DELETED = "deleted"          # terminal — no outbound transitions

# Add to UserProfile class fields (after existing columns)
status: Mapped[ProfileStatus] = mapped_column(
    SAEnum(ProfileStatus, name="profile_status"),
    nullable=False,
    default=ProfileStatus.NEW,
    server_default=ProfileStatus.NEW.value,
)
version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

# Add mapper args for SQLAlchemy optimistic locking
__mapper_args__ = {"version_id_col": version}
```

**How it works:** SQLAlchemy automatically increments `version` on every UPDATE and includes `WHERE version = :expected` in the UPDATE statement. If zero rows match (concurrent modification), `StaleDataError` is raised. The `__mapper_args__` line covers every write path — including plain profile edits — without any hand-written version checks.

---

## 6. Database Migration Required

**Migration file:** `alembic/versions/xxx_add_user_profile_status_and_version.py`

```python
"""Add status and version columns to user_profiles for optimistic locking

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    profile_status = sa.Enum(
        'new', 'verified', 'suspended', 'deleted',
        name='profile_status'
    )
    profile_status.create(op.get_bind(), checkfirst=True)
    op.add_column('user_profiles',
        sa.Column('status', profile_status, nullable=False, server_default='new'))
    op.add_column('user_profiles',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'))

def downgrade():
    op.drop_column('user_profiles', 'version')
    op.drop_column('user_profiles', 'status')
    sa.Enum(name='profile_status').drop(op.get_bind(), checkfirst=True)
```

**Run with:** `alembic revision --autogenerate -m "Add user profile status and version"` then `alembic upgrade head`

---

## 7. Concerns & Mitigations

| Concern | Mitigation |
|---------|------------|
| **PostgreSQL-specific features** | Patterns 6 & 7 require PostgreSQL. Add config check and skip/warn on SQLite. |
| **Demo delays blocking production** | All endpoints live under `/tx-demo`; `ENABLE_DEMO_ENDPOINTS` config flag (default: true in dev, off in prod). The optional `?delay_ms=` hook on the transition endpoint (for showing genuine concurrent overlap in a terminal) must only be active when this flag is set. |
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
| Optimistic Locking | ✅ | ✅ | SQLAlchemy `version_id_col`; 409 vs 400 distinction requires PostgreSQL for reliable concurrent test |
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

5. **Migration** - Add `status` enum + `version` columns to `user_profiles` table
6. **Model Update** - Add `ProfileStatus` enum, `status` + `version` columns, `__mapper_args__` to `UserProfile`
7. **Optimistic Locking** - Implement `ProfileLifecycleService.transition()` + `POST /tx-demo/user-profiles/{id}/transition` with 409/400 dual error paths and two-tab UI

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
| `POST /tx-demo/user-profiles/{id}/transition` | Optimistic Lock | `{target, expected_version}` | Profile (200), 409 Conflict (stale), or 400 Bad Request (illegal transition) |
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
