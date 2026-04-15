# Price Sync Script - Architectural Plan

## 1. Overview

This standalone script fetches real-time prices from external sources (CoinGecko for cryptocurrencies, Yahoo Finance for stocks) and updates the PythonTrio system via its existing REST API. The script operates as an external client, completely decoupled from the main application, using HTTP calls to `GET /assets/` to discover registered assets and `POST /assets/{id}/prices` to record new price snapshots. It runs continuously with a 10-minute interval using the `schedule` library.

## 2. Architecture Decision

Following **Clean Architecture** and **Dependency Inversion**, the script separates price-fetching logic into provider-specific adapters behind a common interface, making it trivial to add new data sources. The **Single Responsibility Principle** is maintained by splitting concerns: asset discovery, price fetching, and API submission are isolated components. This design keeps the script decoupled from the main app—it's just another API consumer—enabling independent deployment and horizontal scaling if needed.

## 3. Implementation Steps

1. **Create the script file** at `scripts/sync_prices.py` with a configuration section at the top for API base URL, schedule interval, and asset-to-symbol mappings (e.g., `{"Bitcoin": "bitcoin", "AAPL": "AAPL"}`).

2. **Implement price provider adapters** with a base protocol/interface:
   - `CoinGeckoProvider`: Uses `requests` to call `/api/v3/simple/price` endpoint (free, no API key required)
   - `YahooFinanceProvider`: Uses `yfinance` library to fetch current quotes
   - Each provider exposes a `fetch_price(symbol: str) -> float | None` method

3. **Implement the main sync loop**:
   - Fetch all assets from `GET /assets/`
   - For each asset, determine provider type from config mapping
   - Call appropriate provider to get current price
   - Submit price via `POST /assets/{id}/prices` with timestamp and source metadata

4. **Add scheduling and error handling**:
   - Use `schedule.every(10).minutes.do(sync_job)`
   - Implement retry logic with exponential backoff for API failures
   - Add logging for successful syncs and failures

5. **Create requirements file** at `scripts/requirements-sync.txt` listing: `requests`, `yfinance`, `schedule`

## 4. Data Flow

The script calls `GET /assets/` to retrieve all registered assets, then iterates through each asset matching its name against a local symbol mapping configuration. Based on asset type (crypto/stock), it routes to the appropriate provider adapter which makes external API calls to CoinGecko or Yahoo Finance. Retrieved prices are then POSTed to `/assets/{id}/prices` with `recorded_at` timestamp and `source` field set to "coingecko" or "yahoo_finance" for audit traceability.

## 5. Concerns & Mitigations

- **Rate limiting**: Both CoinGecko (free tier: ~30 calls/min) and Yahoo Finance have rate limits; mitigate by batching requests and implementing backoff—CoinGecko supports fetching multiple coins in one call.
- **Asset mapping maintenance**: The symbol mapping config must be kept in sync with registered assets; consider adding a `symbol` and `asset_type` field to the Asset model in a future iteration.
- **Network failures**: Implement circuit breaker pattern—if external APIs fail repeatedly, pause and alert rather than flooding with retry requests.
- **Stale prices**: Log warnings if a price couldn't be fetched so operators can investigate missing data.