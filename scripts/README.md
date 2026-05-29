# Scripts Directory

This directory contains standalone scripts for the PythonTrio application.

## Price Sync Script

### Overview

The `sync_prices.py` script is a standalone service that fetches real-time prices from external sources and updates the PythonTrio system via its REST API. It operates as an external client, completely decoupled from the main application.

### Features

- **Multi-Provider Support**: Fetches cryptocurrency prices from CoinGecko and stock prices from Yahoo Finance
- **Clean Architecture**: Provider adapters implement a common Protocol interface
- **Automated Scheduling**: Runs continuously with configurable intervals (default: 10 minutes)
- **Robust Error Handling**: Exponential backoff retry logic for API failures
- **Comprehensive Logging**: Logs all operations to console and file
- **Batch Fetching**: Supports efficient batch price fetching for CoinGecko

### Installation

1. Install required dependencies:

```bash
pip install -r scripts/requirements-sync.txt
```

2. Ensure the PythonTrio API is running:

```bash
# In the project root
uvicorn app.main:app --reload
```

### Configuration

Edit the configuration section at the top of `sync_prices.py`:

```python
# API configuration
API_BASE_URL = "http://localhost:8000"
SYNC_INTERVAL_MINUTES = 10

# Asset-to-symbol mapping
ASSET_SYMBOL_MAP = {
    # Cryptocurrencies (CoinGecko)
    "Bitcoin": {"symbol": "bitcoin", "provider": "coingecko"},
    "Ethereum": {"symbol": "ethereum", "provider": "coingecko"},
    # Stocks (Yahoo Finance)
    "AAPL": {"symbol": "AAPL", "provider": "yahoo"},
    "GOOGL": {"symbol": "GOOGL", "provider": "yahoo"},
}
```

**Important**: Add your registered asset names to the `ASSET_SYMBOL_MAP` dictionary with their corresponding symbols and providers.

### Usage

Run the script from the project root:

```bash
python scripts/sync_prices.py
```

The script will:
1. Run an initial sync immediately
2. Schedule recurring syncs every 10 minutes (configurable)
3. Log all operations to console and `scripts/sync_prices.log`

Press `Ctrl+C` to stop the script gracefully.

### How It Works

1. **Asset Discovery**: Fetches all assets from `GET /assets/`
2. **Symbol Mapping**: Matches asset names against `ASSET_SYMBOL_MAP`
3. **Price Fetching**: Routes to appropriate provider (CoinGecko or Yahoo Finance)
4. **Price Submission**: POSTs to `/assets/{id}/prices` with timestamp and source

### Architecture

The script follows **Clean Architecture** principles:

- **Protocol Interface**: `PriceProvider` protocol defines the contract
- **Provider Adapters**:
  - `CoinGeckoProvider`: Fetches crypto prices from CoinGecko API
  - `YahooFinanceProvider`: Fetches stock prices via yfinance
- **API Client**: `PythonTrioAPIClient` handles all API interactions
- **Sync Service**: `PriceSyncService` orchestrates the sync workflow

### Error Handling

- **Retry Logic**: Exponential backoff for failed requests (max 3 retries)
- **Rate Limiting**: Batch requests where possible (CoinGecko supports batch fetching)
- **Graceful Degradation**: Continues syncing even if individual assets fail
- **Circuit Breaker Pattern**: Logs warnings for missing prices without blocking

### Logging

Logs are written to:
- **Console**: Real-time sync progress
- **File**: `scripts/sync_prices.log` (persistent log history)

Log levels:
- `INFO`: Successful operations and sync summaries
- `WARNING`: Failed price fetches, missing mappings
- `ERROR`: API failures, invalid responses

### Rate Limits

- **CoinGecko Free Tier**: ~30 calls/minute
- **Yahoo Finance**: Generally permissive, but be respectful

The script respects rate limits by:
- Using batch requests where available
- Implementing exponential backoff on failures
- Configurable sync intervals (avoid sub-minute intervals)

### Extending with New Providers

To add a new price provider:

1. Create a new class implementing the `PriceProvider` protocol:

```python
class NewProvider:
    def fetch_price(self, symbol: str) -> float | None:
        # Implementation here
        pass
```

2. Register it in the `PriceSyncService`:

```python
self.providers = {
    "coingecko": coingecko_provider,
    "yahoo": yahoo_provider,
    "new_provider": new_provider,  # Add here
}
```

3. Update `ASSET_SYMBOL_MAP` to use the new provider:

```python
"AssetName": {"symbol": "SYMBOL", "provider": "new_provider"}
```

### Troubleshooting

**Script fails to start:**
- Ensure dependencies are installed: `pip install -r scripts/requirements-sync.txt`
- Check that the API is running at the configured URL

**No prices fetched:**
- Verify asset names in `ASSET_SYMBOL_MAP` match your registered assets
- Check logs for specific error messages
- Test provider APIs manually (CoinGecko/Yahoo Finance may be temporarily down)

**Rate limiting errors:**
- Increase `SYNC_INTERVAL_MINUTES`
- Implement batch fetching for your use case
- Consider using paid API tiers with higher limits

### Production Deployment

For production use:

1. **Run as a systemd service** (Linux):

```ini
[Unit]
Description=PythonTrio Price Sync Service
After=network.target

[Service]
Type=simple
User=pythontrio
WorkingDirectory=/path/to/python_trio
ExecStart=/path/to/venv/bin/python scripts/sync_prices.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Use environment variables** for configuration (instead of hardcoded values)

3. **Set up log rotation** for `sync_prices.log`

4. **Monitor with alerting** on repeated failures

5. **Consider horizontal scaling** by running multiple instances with different asset subsets