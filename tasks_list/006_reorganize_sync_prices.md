# Plan: Reorganize sync_prices.py and Tests

## Summary
Refactor the monolithic `sync_prices.py` into separate modules with clear responsibilities, and reorganize tests to mirror the source structure.

---

## Current Issues

1. **`sync_prices.py` has multiple responsibilities:**
   - Configuration loading
   - API client functions (`fetch_assets`, `record_price`)
   - Sync orchestration logic (`sync_asset_price`, `main`)

2. **Tests are scattered at root level:**
   - `test_coingecko_provider.py`, `test_yfinance_provider.py`, `test_sync_prices.py` all at `tests/` root
   - Should be organized under `tests/scripts/`

3. **Fixtures mixed in main conftest.py:**
   - `mock_assets`, `mock_coingecko_response`, etc. belong with script tests

---

## Target Structure

### Scripts (source)
```
scripts/
├── __init__.py
├── config.py               # NEW: Configuration constants
├── api_client.py           # NEW: API interaction functions
├── sync.py                 # NEW: Sync orchestration logic
├── sync_prices.py          # SIMPLIFIED: Entry point only
└── providers/
    ├── __init__.py         # (unchanged)
    ├── base.py             # (unchanged)
    ├── coingecko.py        # (unchanged)
    └── yfinance_provider.py # (unchanged)
```

### Tests
```
tests/
├── conftest.py             # App fixtures only (remove script fixtures)
├── scripts/
│   ├── __init__.py
│   ├── conftest.py         # NEW: Script-specific fixtures
│   ├── test_api_client.py  # NEW: Tests for api_client.py
│   ├── test_sync.py        # RENAMED: Tests for sync.py
│   └── providers/
│       ├── __init__.py
│       ├── test_coingecko.py   # MOVED from tests/
│       └── test_yfinance.py    # MOVED from tests/
```

---

## Implementation Steps

### Step 1: Create `scripts/config.py`
Extract configuration from sync_prices.py:
```python
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SYNC_TIMEOUT = float(os.getenv("SYNC_TIMEOUT", "30"))
```

### Step 2: Create `scripts/api_client.py`
Extract API functions:
- `fetch_assets(client) -> list[dict]`
- `record_price(client, asset_id, price, asset_type) -> bool`

### Step 3: Create `scripts/sync.py`
Extract orchestration logic:
- `sync_asset_price(client, asset) -> tuple[str, bool, str | None]`
- `run_sync() -> None` (the main sync loop)

### Step 4: Simplify `scripts/sync_prices.py`
Keep only entry point:
```python
import asyncio
from scripts.sync import run_sync

if __name__ == "__main__":
    asyncio.run(run_sync())
```

### Step 5: Create `tests/scripts/` directory structure
- Create `tests/scripts/__init__.py`
- Create `tests/scripts/providers/__init__.py`

### Step 6: Create `tests/scripts/conftest.py`
Move script fixtures from `tests/conftest.py`:
- `mock_assets`
- `mock_coingecko_response`
- `mock_yfinance_info`

### Step 7: Move provider tests
- Move `tests/test_coingecko_provider.py` → `tests/scripts/providers/test_coingecko.py`
- Move `tests/test_yfinance_provider.py` → `tests/scripts/providers/test_yfinance.py`
- Update imports in moved files

### Step 8: Split and move sync tests
- Create `tests/scripts/test_api_client.py` (tests for fetch_assets, record_price)
- Create `tests/scripts/test_sync.py` (tests for sync_asset_price, run_sync)
- Delete `tests/test_sync_prices.py`

### Step 9: Clean up `tests/conftest.py`
Remove moved fixtures (keep only app-related fixtures)

---

## Files to Modify

| Action | File |
|--------|------|
| CREATE | `scripts/config.py` |
| CREATE | `scripts/api_client.py` |
| CREATE | `scripts/sync.py` |
| MODIFY | `scripts/sync_prices.py` (simplify) |
| CREATE | `tests/scripts/__init__.py` |
| CREATE | `tests/scripts/conftest.py` |
| CREATE | `tests/scripts/providers/__init__.py` |
| MOVE   | `tests/test_coingecko_provider.py` → `tests/scripts/providers/test_coingecko.py` |
| MOVE   | `tests/test_yfinance_provider.py` → `tests/scripts/providers/test_yfinance.py` |
| SPLIT  | `tests/test_sync_prices.py` → `tests/scripts/test_api_client.py` + `tests/scripts/test_sync.py` |
| MODIFY | `tests/conftest.py` (remove script fixtures) |

---

## Verification

1. Run all tests: `pytest tests/ -v`
2. Run script manually: `python scripts/sync_prices.py`
3. Verify imports work: `python -c "from scripts.sync import run_sync"`
