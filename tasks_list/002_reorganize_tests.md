# Reorganize Tests to Mirror Code Structure

## Goal
Create 1:1 mapping between `app/` modules and `tests/` modules.

## Target Structure

```
tests/
├── conftest.py                      # Keep as-is
├── test_crud.py                     # ← app/crud.py
├── models/
│   ├── __init__.py
│   ├── test_asset.py                # ← app/models/asset.py
│   ├── test_asset_price_history.py  # ← app/models/asset_price_history.py
│   └── test_portfolio.py            # ← app/models/portfolio.py
└── routers/
    ├── __init__.py
    ├── test_assets.py               # ← app/routers/assets.py
    ├── test_portfolios.py           # ← app/routers/portfolios.py
    └── test_prices.py               # ← app/routers/prices.py
```

## Steps

1. Create directories: `tests/models/`, `tests/routers/` with `__init__.py`
2. Create `tests/test_crud.py` — move CRUD tests from `test_prices.py`
3. Create `tests/routers/test_prices.py` — move API tests from `test_prices.py`
4. Create `tests/routers/test_assets.py` — new tests for `/assets` endpoints
5. Create `tests/routers/test_portfolios.py` — new tests for `/portfolios` endpoints
6. Create `tests/models/test_asset.py` — move `test_model_asset_relationship`
7. Create `tests/models/test_asset_price_history.py` — move `test_model_asset_price_history_relationship`
8. Create `tests/models/test_portfolio.py` — new model tests
9. Delete `tests/test_prices.py`

## Test Migration Map

| From `test_prices.py` | To |
|-----------------------|----|
| `test_record_price_*`, `test_get_*`, edge cases | `test_crud.py` |
| `test_api_*` | `routers/test_prices.py` |
| `test_model_asset_relationship` | `models/test_asset.py` |
| `test_model_asset_price_history_relationship` | `models/test_asset_price_history.py` |
