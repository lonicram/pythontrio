# Transaction Patterns Demo - Architecture Plan

## 1. Overview

This plan extends PythonTrio to demonstrate top database transaction patterns used in production systems. The goal is to create educational, demonstrable endpoints that showcase ACID compliance, concurrency handling, and error recovery strategies using SQLAlchemy and PostgreSQL.

## 2. Current State Assessment

The existing codebase uses basic SQLAlchemy session management with simple `db.add()` + `db.commit()` patterns. There are no explicit transaction boundaries, rollback handling, or locking strategies—making it an ideal starting point for demonstrating these patterns.

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

```
app/
├── services/
│   ├── __init__.py
│   ├── portfolio_service.py      # Rebalancing, valuation, transfer logic
│   └── transaction_demo_service.py  # Isolation level demos
├── routers/
│   └── transaction_demos.py      # All demo endpoints in one router
├── exceptions/
│   ├── __init__.py
│   └── transaction_exceptions.py # PortfolioLimitExceeded, TransferError
└── models/
    └── asset.py                  # Add version column for optimistic locking
```

---

## 5. Database Migration Required

```python
# Alembic migration: add version column for optimistic locking
def upgrade():
    op.add_column('assets', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))

def downgrade():
    op.drop_column('assets', 'version')
```

---

## 6. Concerns & Mitigations

| Concern | Mitigation |
|---------|------------|
| **PostgreSQL-specific features** | Document which patterns require PostgreSQL vs work with SQLite |
| **Demo delays blocking production** | Use separate `/demo/` route prefix; disable in production via config flag |
| **Deadlocks with pessimistic locking** | Document lock ordering; keep locked operations minimal |
| **Optimistic lock retries** | Include `Retry-After` header; document client retry strategy |
| **Isolation level overhead** | SERIALIZABLE has performance cost; document trade-offs |

---

## 7. Recommended Implementation Order

1. **Cross-Table Consistency** - Foundation pattern, easiest to understand
2. **Unit of Work** - Builds on #1, introduces explicit transaction context
3. **Explicit Rollback** - Shows error handling within transactions
4. **Optimistic Locking** - Requires migration, modern concurrency pattern
5. **Savepoints** - Advanced but highly practical for batch operations
6. **Pessimistic Locking** - Contrast with optimistic, shows blocking behavior
7. **Isolation Levels** - Deep educational content, best saved for last

---

## 8. Example API Endpoints Summary

| Endpoint | Pattern | Description |
|----------|---------|-------------|
| `POST /portfolios/with-assets` | Cross-Table | Create portfolio + assets atomically |
| `POST /portfolios/{id}/rebalance` | Unit of Work | Update all asset prices atomically |
| `POST /assets/prices/bulk-import` | Savepoints | Batch import with partial failure recovery |
| `PUT /assets/{id}/price` | Optimistic Lock | Concurrent-safe price update |
| `POST /assets/{id}/transfer` | Explicit Rollback | Move asset with validation |
| `GET /portfolios/{id}/valuation-locked` | Pessimistic Lock | Consistent snapshot calculation |
| `GET /demo/isolation/read-committed` | Isolation Level | Demonstrate phantom reads |
| `GET /demo/isolation/serializable` | Isolation Level | Prevent phantom reads |