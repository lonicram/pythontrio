# Plan: Asset Price Sync Script

## Summary
Create a standalone Python script that fetches current prices for all assets via the existing API, retrieves live prices from free providers (CoinGecko for crypto, Yahoo Finance for stocks), and posts them back to the API. Designed to run as a cron job every 10 minutes.

## Key Findings from Exploration

**Asset Model** (`app/models/asset.py`):
- `code`: ticker symbol (e.g., "BTC", "AAPL")
- `type`: asset category (e.g., "crypto", "stock") - determines which price provider to use

**Existing Endpoints**:
- `GET /assets/` - returns list of all assets
- `POST /prices/` - records a price (requires: `asset_id`, `price`, `currency`, `source`, `recorded_at`)

**No scripts/ folder exists yet** - will create new structure.

---

## Implementation Plan

### Step 1: Add Dependencies
**File**: `requirements.txt`
```
httpx>=0.27.0
yfinance>=0.2.0
```

### Step 2: Create Provider Base Class
**File**: `scripts/providers/base.py`
- Abstract `PriceProvider` class with `async def get_price(code: str) -> Decimal | None`

### Step 3: Implement CoinGecko Provider
**File**: `scripts/providers/coingecko.py`
- Uses free API: `https://api.coingecko.com/api/v3/simple/price`
- Maps codes: BTC→bitcoin, ETH→ethereum, etc.

### Step 4: Implement Yahoo Finance Provider
**File**: `scripts/providers/yfinance_provider.py`
- Uses `yfinance.Ticker(code).info["regularMarketPrice"]`
- Handles stocks/ETFs

### Step 5: Create Provider Registry
**File**: `scripts/providers/__init__.py`
- Maps `type` → provider: `{"crypto": CoinGeckoProvider(), "stock": YFinanceProvider()}`

### Step 6: Create Main Sync Script
**File**: `scripts/sync_prices.py`
- Load `API_BASE_URL` from env (default: `http://localhost:8000`)
- `GET /assets/` → iterate assets
- For each: get provider by type → fetch price → `POST /prices/`
- Log warnings for unfetchable prices
- Log summary at end

### Step 7: Create Init Files
**Files**: `scripts/__init__.py`, `scripts/providers/__init__.py`

---

## New File Structure
```
scripts/
├── __init__.py
├── sync_prices.py          # Main entry point
└── providers/
    ├── __init__.py          # Registry
    ├── base.py              # Abstract base
    ├── coingecko.py         # Crypto prices
    └── yfinance_provider.py # Stock prices
```

---

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Target API base URL |
| `SYNC_TIMEOUT` | `30` | HTTP timeout (seconds) |

---

## Verification
1. Start the API: `uvicorn app.main:app --reload`
2. Create test assets via API (one crypto type="crypto" code="BTC", one stock type="stock" code="AAPL")
3. Run script: `python scripts/sync_prices.py`
4. Check logs for success/failure messages
5. Verify prices recorded: `GET /prices/assets/{id}/history`

---

## Cron Setup
```bash
*/10 * * * * cd /path/to/python_trio && ./venv/bin/python scripts/sync_prices.py >> /var/log/price_sync.log 2>&1
```