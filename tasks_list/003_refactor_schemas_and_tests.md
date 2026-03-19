# Refactor Schemas Module & Reorganize Tests

## Part 1: Schemas Module

### Target Structure
```
app/schemas/
├── __init__.py      # Re-exports all schemas
├── asset.py         # AssetBase, AssetCreate, AssetResponse
├── portfolio.py     # PortfolioBase, PortfolioCreate, PortfolioResponse
└── price.py         # AssetPriceHistory*, AssetPriceChart*
```

### Steps
1. Create `app/schemas/` directory
2. Create `asset.py` — move Asset schemas
3. Create `portfolio.py` — move Portfolio schemas
4. Create `price.py` — move Price schemas (with validators)
5. Create `__init__.py` — re-export all for backward compatibility
6. Delete old `app/schemas.py`

---

## Part 2: Test Reorganization

### Target Structure
```
tests/
├── conftest.py
├── test_crud.py
├── models/
│   ├── test_asset.py
│   ├── test_asset_price_history.py
│   └── test_portfolio.py
└── routers/
    ├── test_assets.py
    ├── test_portfolios.py
    └── test_prices.py
```

### Parametrization Examples

```python
# Consolidate edge case tests
@pytest.mark.parametrize("price", [
    Decimal("0.01"),           # minimum
    Decimal("150.00"),         # normal
    Decimal("9999999999.99"),  # maximum
])
def test_record_price_values(db_session, sample_asset, price): ...

# Consolidate currency tests
@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
def test_record_price_currencies(db_session, sample_asset, currency): ...

# Date filter combinations
@pytest.mark.parametrize("start,end,expected_count", [
    (None, None, 5),
    (day1, None, 4),
    (None, day3, 3),
    (day1, day3, 3),
])
def test_get_history_date_filters(db_session, sample_asset, start, end, expected_count): ...
```

### Migration
| From `test_prices.py` | To |
|-----------------------|----|
| `test_record_price_*`, `test_get_*`, edge cases | `test_crud.py` |
| `test_api_*` | `routers/test_prices.py` |
| `test_model_asset_*` | `models/test_asset.py` |
| `test_model_*_price_history_*` | `models/test_asset_price_history.py` |
