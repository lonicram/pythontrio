# Implementation Plan: Pattern 1 - Cross-Table Consistency

## 1. Overview

This pattern demonstrates atomic transaction handling when creating related entities across multiple tables. The feature creates a Portfolio along with its PortfolioHoldings in a single database transaction, ensuring that if any holding fails validation (e.g., references a non-existent asset), the entire operation rolls back - preventing orphan portfolios. This is a fundamental data consistency pattern critical for financial applications where partial state is unacceptable.

## 2. SQLAlchemy Session & Transaction Concepts

### Session Per Request

Each HTTP request gets its own isolated database session via the `get_db()` dependency:

```python
def get_db():
    db = SessionLocal()   # New session created
    try:
        yield db          # Used during request
    finally:
        db.close()        # Closed after request
```

Sessions are **isolated** - Request A can't see Request B's uncommitted changes. Each session has its own transaction. `db.close()` in `finally` ensures cleanup even on exceptions.

### `flush()` vs `commit()`

| Operation | What it does | Visibility | Reversible? |
|-----------|--------------|------------|-------------|
| `flush()` | Sends SQL to DB, stays in transaction | Only your session | Yes (rollback) |
| `commit()` | Calls flush() + ends transaction | Everyone | No |

**Why this matters:** When creating Portfolio + Holdings, you need the portfolio's ID before creating holdings:

```python
portfolio = Portfolio(name="Tech Fund")
db.add(portfolio)
print(portfolio.id)       # None - not yet sent to DB

db.flush()
print(portfolio.id)       # 42 - ID assigned, but NOT committed yet

holding = PortfolioHolding(
    portfolio_id=portfolio.id,  # Can use 42 now
    asset_id=1,
    quantity=10
)
db.add(holding)
db.commit()               # NOW both are permanent
```

### What Happens on Failure

```
flush()  → INSERT portfolio → id=42 assigned (in transaction)
flush()  → INSERT holding 1 → OK (in transaction)
flush()  → INSERT holding 2 → FK ERROR! (asset doesn't exist)
             ↓
         Exception raised
             ↓
         Session auto-rollback
             ↓
         Portfolio id=42 never existed (to the outside world)
```

### Request Lifecycle Example

```
Request 1 (success)                Request 2 (failure)
───────────────────                ───────────────────
get_db() → Session A               get_db() → Session B
    │                                  │
add(portfolio)                     add(portfolio)
flush() → id=42                    flush() → id=43
add(holding)                       add(holding with bad asset_id)
commit() ✓                         ERROR → auto rollback
    │                                  │
db.close()                         db.close()
    │                                  │
Portfolio 42 exists                Nothing persisted
```

## 3. Architecture Decision

The implementation follows a **Service Layer pattern** to separate business logic from HTTP handling, adhering to the Single Responsibility Principle. The router handles HTTP concerns (request parsing, response formatting, status codes), while the service encapsulates transaction management and business rules. This separation enables unit testing of business logic independent of FastAPI, and allows the service to be reused from other contexts (CLI tools, background jobs). The service will use explicit validation before database writes rather than relying solely on database FK constraints, providing clearer error messages while still benefiting from database-level integrity as a safety net.

## 4. Implementation Steps

**Step 1: Create Pydantic Schemas** (`app/schemas/transaction_demo.py`)
- Define `HoldingInput` schema for individual holding data (asset_id, quantity, purchase_price)
- Define `PortfolioWithHoldingsCreate` request schema containing portfolio name, description, and list of holdings
- Define `PortfolioWithHoldingsResponse` response schema with portfolio data and nested holdings list
- Reuse existing `AssetInfo` and `HoldingResponse` patterns from holdings.py

**Step 2: Create Portfolio Service** (`app/services/portfolio_service.py`)
- Implement `create_with_holdings(db: Session, name: str, description: str | None, holdings: list[HoldingInput]) -> Portfolio`
- Pre-validate all asset_ids exist before any writes (fail fast with clear error)
- Create Portfolio, then create all PortfolioHolding records within single transaction
- Return fully populated Portfolio with holdings relationship loaded
- Raise custom `AssetNotFoundError` for invalid asset_ids (include the specific IDs)

**Step 3: Create Transaction Demos Router** (`app/routers/transaction_demos.py`)
- Create APIRouter with prefix `/tx-demo` and tag `transaction-demos`
- Implement `POST /tx-demo/portfolios/with-holdings` endpoint
- Inject database session via `get_db` dependency
- Call service layer, handle `AssetNotFoundError` with HTTP 400 and clear message
- Register router in `main.py`

**Step 4: Write Integration Tests** (`tests/integration/test_transaction_demos.py`)
- Test success case: create portfolio with 2 valid holdings, verify both entities persisted
- Test rollback case: create portfolio with 2 valid + 1 invalid asset_id, verify HTTP 400, verify no portfolio created
- Test edge case: empty holdings list (should create portfolio with no holdings)
- Test edge case: duplicate asset_ids in request (should fail with clear error)

**Step 5: Update Application Wiring** (`app/main.py`)
- Import transaction_demos router
- Add `app.include_router(transaction_demos.router)`

## 5. Data Flow

```
Request (JSON)
    │
    ▼
Router (transaction_demos.py)
    │ Parse into Pydantic schema
    ▼
PortfolioService.create_with_holdings()
    │
    ├─► Validate all asset_ids exist (single query)
    │       └─► If any missing → raise AssetNotFoundError
    │
    ├─► Create Portfolio
    │       └─► db.add(portfolio)
    │       └─► db.flush() → get portfolio.id
    │
    ├─► Create PortfolioHoldings (loop)
    │       └─► db.add(holding) for each
    │
    └─► db.commit() → atomic persist
            │
            └─► On any exception → automatic rollback
```

## 6. Files to Create

```
app/
  schemas/
    __init__.py           # NEW - empty init
    transaction_demo.py   # NEW - request/response schemas
  services/
    __init__.py           # NEW - empty init
    portfolio_service.py  # NEW - business logic + transaction
  routers/
    transaction_demos.py  # NEW - endpoint definition
tests/
  integration/
    test_transaction_demos.py  # NEW - test cases
```

## 7. Files to Modify

| File | Change |
|------|--------|
| `app/main.py` | Import and register `transaction_demos` router |

## 8. Concerns and Mitigations

| Concern | Mitigation |
|---------|------------|
| **Race Condition**: Asset deleted between validation and insert | DB FK constraint provides ultimate protection; service validation is for user-friendly errors |
| **Performance with large holdings** | Use single `SELECT id FROM assets WHERE id IN (...)` query |
| **Duplicate asset_ids in request** | Service checks for duplicates, returns 400 with clear message |
| **Empty holdings list** | Allow it - valid state (portfolio with no holdings) |

## 9. Code Patterns to Follow

Based on existing codebase:

1. **Pydantic schemas**: Use `model_config = {"from_attributes": True}` for ORM compatibility
2. **Decimal handling**: Use `Decimal` type from `decimal` module, not float
3. **Error responses**: Use `HTTPException` with appropriate status codes
4. **Database sessions**: Use `get_db` dependency injection
5. **Relationship loading**: Use `joinedload()` for eager loading
6. **Type hints**: All function signatures
7. **Docstrings**: Google format

## 10. Test Cases

### Success Case
```python
def test_create_portfolio_with_holdings_success():
    # Given: 2 existing assets
    # When: POST /tx-demo/portfolios/with-holdings with valid data
    # Then: 201 Created, portfolio + 2 holdings in DB
```

### Rollback Case (Primary Demo)
```python
def test_create_portfolio_with_invalid_asset_rollback():
    # Given: 2 existing assets (id=1,2), no asset id=99
    # When: POST with holdings referencing [1, 2, 99]
    # Then: 400 Bad Request, NO portfolio created, NO holdings created
```

### Edge Cases
```python
def test_create_portfolio_empty_holdings():
    # When: POST with empty holdings list
    # Then: 201 Created, portfolio exists with 0 holdings

def test_create_portfolio_duplicate_assets():
    # When: POST with same asset_id twice in holdings
    # Then: 400 Bad Request with clear error message
```
