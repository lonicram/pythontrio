# Price Synchronization Scripts

This directory contains scripts for automated price synchronization of assets.

## Overview

The `sync_prices.py` script fetches current prices for all registered assets and updates them via the FastAPI application's `/prices/` endpoint.

## Features

- **Multiple price providers**: Supports crypto (CoinGecko) and stocks (Yahoo Finance)
- **Async operations**: Efficient price fetching using async/await
- **Robust error handling**: Continues on individual failures, logs detailed errors
- **Configurable**: Environment variables for API URL and timeout
- **Extensible**: Easy to add new price providers

## Usage

### Running the Script

```bash
# Basic usage (uses default http://localhost:8000)
python scripts/sync_prices.py

# With custom API URL
API_BASE_URL=http://api.example.com:8000 python scripts/sync_prices.py
```

### Configuration

Environment variables:

- `API_BASE_URL`: Base URL of your FastAPI application (default: `http://localhost:8000`)
- `SYNC_TIMEOUT`: HTTP timeout in seconds (default: `30`)

### Cron Setup

To run every 10 minutes:

```bash
*/10 * * * * cd /path/to/python_trio && ./venv/bin/python scripts/sync_prices.py >> /var/log/price_sync.log 2>&1
```

## Architecture

### Directory Structure

```
scripts/
├── __init__.py
├── sync_prices.py          # Main orchestration script
├── README.md              # This file
└── providers/
    ├── __init__.py         # Provider registry
    ├── base.py            # Abstract base class
    ├── coingecko.py       # Cryptocurrency price provider
    └── yfinance_provider.py # Stock price provider
```

### Price Providers

#### CoinGeckoProvider (Crypto)

- **API**: CoinGecko public API (no auth required)
- **Supported coins**: BTC, ETH, USDT, BNB, SOL, USDC, XRP, ADA, DOGE, TRX, AVAX, MATIC, DOT, LTC, LINK
- **Rate limits**: ~50 calls/minute (free tier)

#### YFinanceProvider (Stocks)

- **API**: Yahoo Finance via yfinance library
- **Supported**: Any valid stock ticker
- **Rate limits**: Reasonable usage (no strict limits)

### Adding New Providers

1. Create a new provider class in `scripts/providers/`
2. Inherit from `PriceProvider` base class
3. Implement the `async get_price(code: str) -> Decimal | None` method
4. Register in `PROVIDER_REGISTRY` in `scripts/providers/__init__.py`

Example:

```python
from scripts.providers.base import PriceProvider

class ForexProvider(PriceProvider):
    async def get_price(self, code: str) -> Decimal | None:
        # Implementation here
        pass

# Register in __init__.py
PROVIDER_REGISTRY["forex"] = ForexProvider()
```

## Error Handling

The script handles these scenarios gracefully:

- **Unknown asset type**: Logs warning, skips asset
- **API rate limits**: Logs error, continues with next asset
- **Network timeouts**: Logs error, continues with next asset
- **Invalid ticker codes**: Provider returns None, logged as warning
- **Empty asset list**: Logs info, exits cleanly
- **API endpoint failures**: Logs detailed error, continues

## Output

Example output:

```
2024-03-20 10:00:00 - INFO - ============================================================
2024-03-20 10:00:00 - INFO - Starting price sync
2024-03-20 10:00:00 - INFO - API Base URL: http://localhost:8000
2024-03-20 10:00:00 - INFO - ============================================================
2024-03-20 10:00:00 - INFO - Fetching assets...
2024-03-20 10:00:00 - INFO - Found 3 asset(s) to sync
2024-03-20 10:00:00 - INFO - ------------------------------------------------------------
2024-03-20 10:00:01 - INFO - ✓ Bitcoin (BTC): $67234.50
2024-03-20 10:00:02 - INFO - ✓ Apple Inc. (AAPL): $178.25
2024-03-20 10:00:03 - WARNING - No price available for Unknown Asset (XYZ)
2024-03-20 10:00:03 - INFO - ------------------------------------------------------------
2024-03-20 10:00:03 - INFO - Sync complete
2024-03-20 10:00:03 - INFO - Successful: 2
2024-03-20 10:00:03 - INFO - Failed: 1
2024-03-20 10:00:03 - WARNING - Failed assets:
2024-03-20 10:00:03 - WARNING -   - Unknown Asset: No price available
2024-03-20 10:00:03 - INFO - ============================================================
```

## Testing

Before deploying to cron:

1. Ensure the FastAPI application is running
2. Add test assets of different types (crypto, stock)
3. Run the script manually: `python scripts/sync_prices.py`
4. Check logs for any errors
5. Verify prices in database: Query `/prices/assets/{asset_id}/history`

## Dependencies

- `httpx>=0.27.0`: Async HTTP client
- `yfinance>=0.2.0`: Yahoo Finance data wrapper

Already included in `requirements.txt`.

## Rollback

To undo a sync (delete price records):

```sql
DELETE FROM asset_price_history
WHERE source LIKE 'sync_%'
AND recorded_at BETWEEN '2024-03-20 10:00:00' AND '2024-03-20 10:10:00';
```

## Monitoring

Key metrics to monitor:

- **Success rate**: Ratio of successful to total assets
- **Execution time**: Should complete within timeout window
- **API errors**: Watch for rate limiting or network issues
- **Missing prices**: Assets consistently failing to fetch prices

## Security

- No API keys stored in code (CoinGecko/YFinance are public)
- Read-only access to assets endpoint
- Write-only access to prices endpoint
- No destructive operations
