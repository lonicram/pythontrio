# Test Architecture Plan for PythonTrio

## 1. Overview

The project lacks any test infrastructure. We need to introduce pytest with fixtures for database isolation, FastAPI TestClient for API testing, and proper mocking for external services. The test suite will cover models, API endpoints, business logic, and the price sync script, following the testing pyramid (unit tests at base, integration tests above, and a few E2E tests at top).

## 2. Architecture Decision

Following **Clean Architecture** principles, tests will be organized by layer: unit tests for models/domain logic, integration tests for API endpoints with database, and isolated tests for external dependencies using mocking. We apply **Dependency Inversion** by leveraging pytest fixtures to inject test databases and mock providers. The test database will use SQLite in-memory for speed, ensuring fast feedback cycles (**KISS**).

## 3. Implementation Steps

### Step 1: Add pytest dependencies to `requirements-dev.txt`

```
pytest>=8.0.0
pytest-cov>=4.1.0
httpx>=0.27.0
```

### Step 2: Create test directory structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (test DB, client, factories)
├── unit/
│   ├── __init__.py
│   ├── test_models.py       # Model unit tests
│   └── test_config.py       # Config tests
├── integration/
│   ├── __init__.py
│   ├── test_main.py         # Root and health endpoints
│   ├── test_assets_api.py
│   ├── test_portfolios_api.py
│   ├── test_holdings_api.py
│   └── test_asset_prices_api.py
└── scripts/
    ├── __init__.py
    └── test_sync_prices.py  # Script tests with mocked external APIs
```

### Step 3: Implement core fixtures in `conftest.py`

- `engine` fixture: In-memory SQLite
- `db_session` fixture: Transaction rollback per test
- `client` fixture: FastAPI TestClient with dependency override
- Factory functions for creating test entities

### Step 4: Write test modules following priority

1. API endpoint tests (highest business value)
2. Model tests (validation, relationships)
3. Script tests (sync_prices with mocked providers)

### Step 5: Configure pytest in `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --cov=app --cov-report=term-missing --cov-fail-under=80"
```

## 4. Data Flow

Test fixtures follow a dependency chain: `engine` -> `Base.metadata.create_all` -> `db_session` (scoped per test, auto-rollbacks) -> `client` (FastAPI TestClient with overridden `get_db`). Each test receives an isolated database state. For script tests, providers are mocked via `unittest.mock.patch` or pytest-mock, preventing external API calls while validating the sync service orchestration.

## 5. Concerns & Mitigations

| Concern | Mitigation |
|---------|------------|
| **SQLite vs PostgreSQL differences** | Use SQLite for speed; add CI job with PostgreSQL for full compatibility testing |
| **External API flakiness in script tests** | 100% mock coverage for CoinGecko/Yahoo; no real network calls in tests |
| **Test database cleanup** | Use transaction rollback pattern (no manual cleanup needed) |
| **Coverage gaps** | Set minimum coverage threshold (80%); fail CI if below |
| **Slow test suite** | In-memory DB + parallel execution (`pytest-xdist` if needed) |

---

## Proposed Tests by Module

### `tests/unit/test_models.py`

| Test Case | Purpose |
|-----------|---------|
| `test_asset_creation` | Verify Asset model instantiation with all fields |
| `test_asset_repr` | Check `__repr__` format |
| `test_portfolio_total_value_empty` | Portfolio with no holdings returns 0 |
| `test_portfolio_total_value_with_holdings` | Correct sum with prices |
| `test_portfolio_total_value_ignores_null_prices` | Skips assets without price |
| `test_portfolio_holding_repr` | Check `__repr__` format |

### `tests/unit/test_config.py`

| Test Case | Purpose |
|-----------|---------|
| `test_default_settings` | Verify default values load |
| `test_settings_from_env` | Mock env vars and verify override |

### `tests/integration/test_assets_api.py`

| Test Case | Purpose |
|-----------|---------|
| `test_list_assets_empty` | GET /assets/ returns empty list |
| `test_create_asset` | POST /assets/ creates and returns asset |
| `test_create_asset_with_price` | Decimal price stored correctly |
| `test_get_asset_by_id` | GET /assets/{id} returns asset |
| `test_get_asset_not_found` | GET /assets/{id} returns 404 |
| `test_update_asset` | PUT /assets/{id} modifies fields |
| `test_update_asset_not_found` | PUT /assets/{id} returns 404 |
| `test_delete_asset` | DELETE /assets/{id} removes asset |
| `test_delete_asset_not_found` | DELETE /assets/{id} returns 404 |

### `tests/integration/test_portfolios_api.py`

| Test Case | Purpose |
|-----------|---------|
| `test_list_portfolios_empty` | GET /portfolios/ returns empty |
| `test_create_portfolio` | POST creates portfolio |
| `test_get_portfolio_by_id` | GET returns portfolio |
| `test_get_portfolio_not_found` | Returns 404 |
| `test_update_portfolio` | PUT modifies portfolio |
| `test_delete_portfolio` | DELETE removes portfolio |

### `tests/integration/test_holdings_api.py`

| Test Case | Purpose |
|-----------|---------|
| `test_list_holdings_empty` | GET /portfolios/{id}/holdings returns empty |
| `test_add_holding` | POST creates holding with asset info |
| `test_add_holding_portfolio_not_found` | Returns 404 |
| `test_add_holding_asset_not_found` | Returns 404 |
| `test_add_holding_duplicate` | Returns 409 conflict |
| `test_update_holding_quantity` | PUT modifies holding |
| `test_update_holding_not_found` | Returns 404 |
| `test_remove_holding` | DELETE removes holding |

### `tests/integration/test_asset_prices_api.py`

| Test Case | Purpose |
|-----------|---------|
| `test_create_asset_price` | POST creates price record |
| `test_create_asset_price_updates_asset` | Asset.price updated (denormalization) |
| `test_create_asset_price_asset_not_found` | Returns 404 |
| `test_create_asset_price_id_mismatch` | Returns 400 |
| `test_get_price_history` | GET returns chart response |
| `test_get_price_history_with_date_filter` | Date range filtering works |
| `test_get_price_history_pagination` | limit/offset work |
| `test_get_latest_price` | GET /latest returns most recent |
| `test_get_latest_price_no_history` | Returns 404 |

### `tests/integration/test_main.py`

| Test Case | Purpose |
|-----------|---------|
| `test_root_endpoint` | GET / returns welcome message |
| `test_health_endpoint` | GET /health returns healthy |

### `tests/scripts/test_sync_prices.py`

| Test Case | Purpose |
|-----------|---------|
| `test_coingecko_provider_success` | Mocked API returns price |
| `test_coingecko_provider_network_error` | Returns None on failure |
| `test_coingecko_batch_fetch` | Multiple symbols in one call |
| `test_yahoo_provider_success` | Mocked yfinance returns price |
| `test_yahoo_provider_failure` | Returns None on error |
| `test_api_client_fetch_assets` | Mocked GET returns assets |
| `test_api_client_submit_price` | Mocked POST succeeds |
| `test_retry_with_exponential_backoff_success` | Returns on first success |
| `test_retry_with_exponential_backoff_failure` | Returns None after max retries |
| `test_sync_service_sync_all_prices` | Orchestrates full sync |
| `test_sync_service_skips_unmapped_assets` | Ignores unknown assets |

---

## Estimated Coverage Impact

| Module | Current | After Tests |
|--------|---------|-------------|
| `app/models/` | 0% | ~90% |
| `app/routers/` | 0% | ~95% |
| `app/config.py` | 0% | ~100% |
| `app/database.py` | 0% | ~80% |
| `app/main.py` | 0% | ~100% |
| `scripts/sync_prices.py` | 0% | ~85% |

---

## Sample `conftest.py` Structure

```python
"""Shared pytest fixtures for PythonTrio tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create FastAPI TestClient with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

---

## Next Steps

1. Implement `requirements-dev.txt` updates
2. Create `tests/` directory structure
3. Implement `conftest.py` with fixtures
4. Write integration tests for API endpoints (highest priority)
5. Write unit tests for models
6. Write script tests with mocks
7. Add pytest configuration to `pyproject.toml`
8. Run coverage report and iterate until 80%+ coverage achieved