"""Standalone price synchronization script for PythonTrio.

This script fetches real-time prices from external sources (CoinGecko for
cryptocurrencies, Yahoo Finance for stocks) and updates the PythonTrio system
via its REST API. It operates as an external client, completely decoupled from
the main application.

Architecture:
- Provider adapters follow Dependency Inversion (Protocol interface)
- Single Responsibility: asset discovery, price fetching, API submission
- Runs continuously with 10-minute intervals using schedule library

Usage:
    python scripts/sync_prices.py
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Protocol, TypeVar

import requests
import schedule
import yfinance as yf

# Type variable for retry function
T = TypeVar("T")

# ============================================================================
# Configuration
# ============================================================================

# API configuration
API_BASE_URL = "http://localhost:8000"
SYNC_INTERVAL_MINUTES = 1

# Asset-to-symbol mapping
# Maps asset names to their provider symbols and types
ASSET_SYMBOL_MAP = {
    # Cryptocurrencies (CoinGecko)
    "Bitcoin": {"symbol": "bitcoin", "provider": "coingecko"},
    "Ethereum": {"symbol": "ethereum", "provider": "coingecko"},
    "BTC": {"symbol": "bitcoin", "provider": "coingecko"},
    "ETH": {"symbol": "ethereum", "provider": "coingecko"},
    # Stocks (Yahoo Finance)
    "AAPL": {"symbol": "AAPL", "provider": "yahoo"},
    "GOOGL": {"symbol": "GOOGL", "provider": "yahoo"},
    "MSFT": {"symbol": "MSFT", "provider": "yahoo"},
    "TSLA": {"symbol": "TSLA", "provider": "yahoo"},
    "Apple": {"symbol": "AAPL", "provider": "yahoo"},
    "Google": {"symbol": "GOOGL", "provider": "yahoo"},
    "Microsoft": {"symbol": "MSFT", "provider": "yahoo"},
    "Tesla": {"symbol": "TSLA", "provider": "yahoo"},
}

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1
MAX_BACKOFF_SECONDS = 60

# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scripts/sync_prices.log"),
    ],
)

logger = logging.getLogger(__name__)

# ============================================================================
# Price Provider Protocol and Implementations
# ============================================================================


class PriceProvider(Protocol):
    """Protocol interface for price providers.

    This interface enables Dependency Inversion - new providers can be added
    without modifying existing code.
    """

    def fetch_price(self, symbol: str) -> float | None:
        """Fetch current price for a given symbol.

        Args:
            symbol: The symbol to fetch the price for.

        Returns:
            The current price as a float, or None if unavailable.
        """
        ...
        pass


class CoinGeckoProvider:
    """Price provider for cryptocurrency prices from CoinGecko API.

    Uses the free CoinGecko API (no API key required).
    Rate limit: ~30 calls/minute on free tier.
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, timeout: int = 10):
        """Initialize CoinGecko provider.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_price(self, symbol: str) -> float | None:
        """Fetch cryptocurrency price from CoinGecko.

        Args:
            symbol: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum').

        Returns:
            Current price in USD, or None if fetch failed.
        """
        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": symbol,
                "vs_currencies": "usd",
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            if symbol in data and "usd" in data[symbol]:
                price = data[symbol]["usd"]
                logger.info(f"CoinGecko: Fetched {symbol} = ${price:,.2f}")
                return float(price)
            else:
                logger.warning(f"CoinGecko: No price data for {symbol}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko: Failed to fetch {symbol}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"CoinGecko: Invalid response for {symbol}: {e}")
            return None

    def fetch_batch_prices(self, symbols: list[str]) -> dict[str, float]:
        """Fetch multiple cryptocurrency prices in a single API call.

        This is more efficient for fetching multiple prices and helps with
        rate limiting.

        Args:
            symbols: List of CoinGecko coin IDs.

        Returns:
            Dictionary mapping symbols to prices.
        """
        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": ",".join(symbols),
                "vs_currencies": "usd",
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            results = {}
            for symbol in symbols:
                if symbol in data and "usd" in data[symbol]:
                    results[symbol] = float(data[symbol]["usd"])

            logger.info(f"CoinGecko: Batch fetched {len(results)} prices")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko: Batch fetch failed: {e}")
            return {}


class YahooFinanceProvider:
    """Price provider for stock prices from Yahoo Finance.

    Uses the yfinance library which wraps Yahoo Finance API.
    Generally more reliable than direct API calls.
    """

    def __init__(self, timeout: int = 10):
        """Initialize Yahoo Finance provider.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout

    def fetch_price(self, symbol: str) -> float | None:
        """Fetch stock price from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'GOOGL').

        Returns:
            Current price in USD, or None if fetch failed.
        """
        try:
            ticker = yf.Ticker(symbol)

            # Get current price from fast_info (faster than full info)
            # Fallback to info if fast_info is not available
            try:
                price = ticker.fast_info.last_price
            except AttributeError:
                info = ticker.info
                price = info.get("regularMarketPrice") or info.get("currentPrice")

            if price is None:
                logger.warning(f"Yahoo Finance: No price data for {symbol}")
                return None

            logger.info(f"Yahoo Finance: Fetched {symbol} = ${price:,.2f}")
            return float(price)

        except Exception as e:
            logger.error(f"Yahoo Finance: Failed to fetch {symbol}: {e}")
            return None


# ============================================================================
# API Client
# ============================================================================


class PythonTrioAPIClient:
    """Client for interacting with PythonTrio REST API."""

    def __init__(self, base_url: str, timeout: int = 10):
        """Initialize API client.

        Args:
            base_url: Base URL of the PythonTrio API.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_assets(self) -> list[dict[str, Any]] | None:
        """Fetch all assets from the API.

        Returns:
            List of asset dictionaries, or None if fetch failed.
        """
        try:
            url = f"{self.base_url}/assets/"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            assets: list[dict[str, Any]] = response.json()
            logger.info(f"API: Fetched {len(assets)} assets")
            return assets

        except requests.exceptions.RequestException as e:
            logger.error(f"API: Failed to fetch assets: {e}")
            return None

    def submit_price(
        self,
        asset_id: int,
        price: float,
        source: str,
        recorded_at: datetime | None = None,
    ) -> bool:
        """Submit a price record for an asset.

        Args:
            asset_id: ID of the asset.
            price: Price value.
            source: Source of the price data (e.g., 'coingecko', 'yahoo_finance').
            recorded_at: Timestamp when price was recorded (defaults to now).

        Returns:
            True if submission succeeded, False otherwise.
        """
        if recorded_at is None:
            recorded_at = datetime.now()

        try:
            url = f"{self.base_url}/assets/{asset_id}/prices"
            payload = {
                "asset_id": asset_id,
                "price": price,
                "recorded_at": recorded_at.isoformat(),
                "source": source,
            }

            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            logger.info(
                f"API: Submitted price for asset {asset_id}: ${price:,.2f} "
                f"(source: {source})"
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"API: Failed to submit price for asset {asset_id}: {e}")
            return False


# ============================================================================
# Retry Logic
# ============================================================================


def retry_with_exponential_backoff(
    func: Callable[[], T | None], max_retries: int = MAX_RETRIES
) -> T | None:
    """Retry a function with exponential backoff.

    Args:
        func: Function to retry (should return None on failure).
        max_retries: Maximum number of retries.

    Returns:
        Function result, or None if all retries failed.
    """
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(max_retries):
        result = func()

        if result is not None:
            return result

        if attempt < max_retries - 1:
            wait_time = min(backoff, MAX_BACKOFF_SECONDS)
            logger.warning(f"Retry attempt {attempt + 1}/{max_retries} in {wait_time}s")
            time.sleep(wait_time)
            backoff *= 2

    logger.error(f"All {max_retries} retry attempts failed")
    return None


# ============================================================================
# Main Sync Logic
# ============================================================================


class PriceSyncService:
    """Service orchestrating price synchronization."""

    def __init__(
        self,
        api_client: PythonTrioAPIClient,
        coingecko_provider: PriceProvider, # CoinGeckoProvider
        yahoo_provider: PriceProvider,
    ):
        """Initialize sync service.

        Args:
            api_client: PythonTrio API client.
            coingecko_provider: CoinGecko price provider.
            yahoo_provider: Yahoo Finance price provider.
        """
        self.api_client = api_client
        self.providers: dict[str, PriceProvider] = {
            "coingecko": coingecko_provider,
            "yahoo": yahoo_provider,
        }

    def sync_all_prices(self) -> None:
        """Fetch and sync prices for all registered assets.

        This is the main sync job that runs on schedule.
        """
        logger.info("=" * 70)
        logger.info("Starting price sync job")
        logger.info("=" * 70)

        # Fetch assets with retry
        assets = retry_with_exponential_backoff(self.api_client.fetch_assets)

        if not assets:
            logger.error("Failed to fetch assets, skipping sync")
            return

        # Track sync statistics
        success_count = 0
        failed_count = 0
        skipped_count = 0

        sync_timestamp = datetime.now()

        # Process each asset
        for asset in assets:
            asset_id = asset["id"]
            asset_name = asset["name"]

            # Check if asset is in our mapping
            if asset_name not in ASSET_SYMBOL_MAP:
                logger.debug(f"Asset '{asset_name}' not in symbol mapping, skipping")
                skipped_count += 1
                continue

            mapping = ASSET_SYMBOL_MAP[asset_name]
            symbol = mapping["symbol"]
            provider_type = mapping["provider"]

            # Get appropriate provider
            provider = self.providers.get(provider_type)
            if not provider:
                logger.error(f"Unknown provider type: {provider_type}")
                failed_count += 1
                continue

            # Fetch price
            price = provider.fetch_price(symbol)

            if price is None:
                logger.warning(f"Failed to fetch price for {asset_name} ({symbol})")
                failed_count += 1
                continue

            # Submit price to API
            source = "coingecko" if provider_type == "coingecko" else "yahoo_finance"
            success = self.api_client.submit_price(
                asset_id=asset_id,
                price=price,
                source=source,
                recorded_at=sync_timestamp,
            )

            if success:
                success_count += 1
            else:
                failed_count += 1

        # Log summary
        logger.info("-" * 70)
        logger.info(
            f"Sync completed: {success_count} succeeded, {failed_count} failed, "
            f"{skipped_count} skipped"
        )
        logger.info("=" * 70)


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Main entry point for the price sync script."""
    logger.info("=" * 70)
    logger.info("Price Sync Script Starting")
    logger.info(f"API Base URL: {API_BASE_URL}")
    logger.info(f"Sync Interval: {SYNC_INTERVAL_MINUTES} minutes")
    logger.info("=" * 70)

    # Initialize components
    api_client = PythonTrioAPIClient(API_BASE_URL)
    coingecko_provider = CoinGeckoProvider()
    yahoo_provider = YahooFinanceProvider()

    sync_service = PriceSyncService(
        api_client=api_client,
        coingecko_provider=coingecko_provider,
        yahoo_provider=yahoo_provider,
    )

    # Run immediately on startup
    logger.info("Running initial sync...")
    try:
        sync_service.sync_all_prices()
    except Exception as e:
        logger.error(f"Initial sync failed: {e}", exc_info=True)

    # Schedule recurring syncs
    schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_service.sync_all_prices)

    logger.info(f"Scheduled sync every {SYNC_INTERVAL_MINUTES} minutes")
    logger.info("Press Ctrl+C to stop")

    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, exiting...")
    except Exception as e:
        logger.error(f"Unexpected error in scheduler loop: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()