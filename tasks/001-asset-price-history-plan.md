# Asset Price History - Architecture Plan

## 1. Overview

This feature introduces a time-series data model to store historical asset prices for charting and analytics. The solution creates a separate `AssetPrice` table with a one-to-many relationship to `Asset`, allowing efficient storage and querying of price snapshots. A cronjob will periodically insert new price records, while dedicated endpoints will serve chart data with flexible time-range filtering and aggregation options.

## 2. Architecture Decision

**Pattern: Time-Series Append-Only Table with Composite Index**

Following the **Single Responsibility Principle**, we separate the current price (kept in `Asset.price` for quick access) from historical data (stored in `AssetPrice`). This avoids query overhead when only the latest price is needed. The `AssetPrice` table follows an append-only pattern—prices are never updated, only inserted—which simplifies concurrency and enables efficient bulk writes from the cronjob. A composite index on `(asset_id, recorded_at)` ensures fast range queries for chart rendering.

## 3. Implementation Steps

1. **Create `AssetPrice` model** (`app/models/asset_price.py`)
   - Fields: `id`, `asset_id` (FK), `price` (Float), `recorded_at` (DateTime), `source` (String, optional)
   - Add composite index on `(asset_id, recorded_at DESC)`
   - Add relationship to `Asset` model with `back_populates`

2. **Generate Alembic migration**
   - Run `alembic revision --autogenerate -m "add_asset_price_history_table"`
   - Review and apply migration

3. **Create Pydantic schemas** (`app/schemas/asset_price.py`)
   - `AssetPriceCreate`: For cronjob bulk inserts
   - `AssetPriceBulkCreate`: List wrapper for batch operations
   - `AssetPriceResponse`: Single price record
   - `AssetPriceChartResponse`: Optimized for chart rendering (list with metadata)

4. **Create price history router** (`app/routers/asset_prices.py`)
   - `POST /assets/{asset_id}/prices` - Insert single price (cronjob)
   - `POST /assets/prices/bulk` - Bulk insert prices (cronjob, primary)
   - `GET /assets/{asset_id}/prices` - Get price history with filters
   - `GET /assets/{asset_id}/prices/latest` - Get most recent price

5. **Update `Asset` model and router**
   - Add `prices` relationship to `Asset` model
   - Optionally update `Asset.price` when new price is inserted (denormalization for fast reads)

## 4. Data Flow

```
Cronjob → POST /assets/prices/bulk → AssetPriceRouter → DB (bulk insert)
                                                     ↓
                                            Update Asset.price (latest)

Frontend → GET /assets/{id}/prices?from=X&to=Y → AssetPriceRouter → DB Query
                                                                  ↓
                                              Return filtered, paginated results
```

The cronjob calls the bulk insert endpoint with an array of `{asset_id, price, recorded_at}` objects. The endpoint performs a single transaction insert and optionally updates each asset's current price. Chart requests query the `AssetPrice` table with `asset_id` filter and `recorded_at` range, returning results ordered by timestamp. Pagination via `limit/offset` or cursor-based approach keeps response sizes manageable.

## 5. Concerns & Mitigations

| Concern | Mitigation |
|---------|------------|
| **Table growth** - Price history grows unbounded | Add a retention policy; consider partitioning by date or archiving old data to cold storage |
| **Query performance** - Large datasets slow down chart queries | Composite index `(asset_id, recorded_at DESC)` + enforce `limit` on queries; consider pre-aggregated tables for long time ranges |
| **Bulk insert performance** - Cronjob may insert thousands of records | Use `bulk_insert_mappings()` or `executemany` for efficient batch inserts |
| **Timezone handling** - Inconsistent timestamps | Store all `recorded_at` as UTC; convert to user timezone on frontend |
| **Duplicate entries** - Cronjob may run twice | Add unique constraint on `(asset_id, recorded_at)` or use upsert logic |

---

## Proposed Data Model

```
┌─────────────────┐         ┌──────────────────────┐
│     Asset       │         │     AssetPrice       │
├─────────────────┤         ├──────────────────────┤
│ id (PK)         │◄───────┤│ id (PK)              │
│ name            │   1:N   │ asset_id (FK)        │
│ description     │         │ price (Float)        │
│ price (current) │         │ recorded_at (DateTime)│
│ portfolio_id    │         │ source (String?)     │
└─────────────────┘         │ created_at (DateTime)│
                            └──────────────────────┘
                            INDEX: (asset_id, recorded_at DESC)
```
