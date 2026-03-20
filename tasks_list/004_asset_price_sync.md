# Implementation Plan: Asset Price Sync Script

## Overview

Create a standalone Python script that fetches current prices for all assets registered in the system and updates them via the existing API. The script will use free public APIs (CoinGecko for crypto, Yahoo Finance for stocks) and is designed to run as a scheduled cron job every 10 minutes.

## Prerequisites

- Existing FastAPI app running with `/assets/` and `/prices/` endpoints
- Understanding that `Asset.code` contains the ticker symbol (e.g., "BTC", "AAPL")
- Understanding that `Asset.type` determines which price provider to use

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Script location | `scripts/sync_prices.py` | Keeps scheduled jobs separate from app code |
| HTTP client | `httpx` | Async-capable, modern, already common in FastAPI projects |
| Crypto prices | CoinGecko API | Free, no API key required, reliable |
| Stock prices | `yfinance` library | Free, no API key, wraps Yahoo Finance |
| Configuration | Environment variables | Consistent with existing app config pattern |

---

## Implementation Steps

### Step 1: Add Dependencies

**What**: Add required packages for the sync script
**Where**: `requirements.txt`
**How**: Append:
```
httpx>=0.27.0
yfinance>=0.2.0
```

---

### Step 2: Create Price Provider Interface

**What**: Abstract base class for price providers
**Where**: `scripts/providers/__init__.py` and `scripts/providers/base.py`

```python
# scripts/providers/base.py
class PriceProvider(ABC):
    @abstractmethod
    async def get_price(self, code: str) -> Decimal | None:
        """Return current price or None if unavailable."""
        pass
```

**Why**: Allows easy addition of new price sources later (forex, commodities).

---

### Step 3: Implement CoinGecko Provider

**What**: Crypto price provider using CoinGecko's free API
**Where**: `scripts/providers/coingecko.py`

**Key details**:
- Endpoint: `https://api.coingecko.com/api/v3/simple/price`
- Maps common codes (BTC->bitcoin, ETH->ethereum) via lookup dict
- Returns `None` on failure (handled upstream)

---

### Step 4: Implement Yahoo Finance Provider

**What**: Stock price provider using `yfinance`
**Where**: `scripts/providers/yfinance_provider.py`

**Key details**:
- Use `yfinance.Ticker(code).info["regularMarketPrice"]`
- Wrap in try/except to handle delisted/invalid tickers
- Returns `None` on failure

---

### Step 5: Create Provider Registry

**What**: Map asset types to their price providers
**Where**: `scripts/providers/__init__.py`

```python
PROVIDER_REGISTRY: dict[str, PriceProvider] = {
    "crypto": CoinGeckoProvider(),
    "stock": YFinanceProvider(),
}
```

---

### Step 6: Create Main Sync Script

**What**: Orchestration script that syncs all asset prices
**Where**: `scripts/sync_prices.py`

**Flow**:
```
1. Load config (API_BASE_URL from env)
2. GET /assets/ -> list of assets
3. For each asset:
   a. Get provider by asset.type
   b. Fetch price via provider
   c. If price found -> POST /prices/
   d. If price not found -> log warning
4. Log summary (success count, failure count)
```

**Critical code pattern** (POST to /prices/):
```python
payload = {
    "asset_id": asset["id"],
    "price": str(price),
    "currency": "USD",
    "source": f"sync_{asset['type']}",
    "recorded_at": datetime.utcnow().isoformat()
}
await client.post(f"{API_BASE_URL}/prices/", json=payload)
```

---

### Step 7: Add Logging Configuration

**What**: Structured logging for cron job monitoring
**Where**: Top of `scripts/sync_prices.py`

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
```

Log these events:
- Script start/end
- Each asset processed (success/failure)
- Summary statistics

---

### Step 8: Create Entry Point

**What**: CLI entry point with error handling
**Where**: Bottom of `scripts/sync_prices.py`

```python
if __name__ == "__main__":
    asyncio.run(main())
```

---

## File Structure (New Files)

```
scripts/
    __init__.py
    sync_prices.py          # Main orchestration
    providers/
        __init__.py          # Registry + exports
        base.py              # Abstract base class
        coingecko.py         # Crypto provider
        yfinance_provider.py # Stock provider
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Base URL of your FastAPI app |
| `SYNC_TIMEOUT` | `30` | HTTP timeout in seconds |

---

## Testing Strategy

1. **Unit tests** for each provider (mock HTTP responses)
2. **Integration test**: Run against local API with test assets
3. **Manual verification**: Add a crypto and stock asset, run script, check `/prices/` endpoint

---

## Cron Setup Example

```bash
*/10 * * * * cd /path/to/python_trio && ./venv/bin/python scripts/sync_prices.py >> /var/log/price_sync.log 2>&1
```

---

## Rollback Considerations

- Script is read-only for assets, write-only for prices
- No destructive operations
- To "undo": delete price records from `asset_price_history` table for specific time range

---

## Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| Unknown asset type | Log warning, skip asset |
| API rate limit | Log error, continue with next asset |
| Network timeout | Log error, continue with next asset |
| Invalid ticker code | Provider returns `None`, logged as warning |
| Empty asset list | Log info, exit cleanly |

---

**Estimated implementation time**: 1-2 hours