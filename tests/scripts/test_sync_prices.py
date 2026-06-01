"""Unit tests for the sync_prices script.

Tests cover the main components of the price synchronization script:
- CoinGeckoProvider: Cryptocurrency price fetching
- YahooFinanceProvider: Stock price fetching
- PythonTrioAPIClient: API interactions
- retry_with_exponential_backoff: Retry logic
- PriceSyncService: Orchestration of the sync process
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from scripts.sync_prices import (
    CoinGeckoProvider,
    PriceSyncService,
    PythonTrioAPIClient,
    YahooFinanceProvider,
    retry_with_exponential_backoff,
)


# ============================================================================
# CoinGeckoProvider Tests
# ============================================================================


class TestCoinGeckoProvider:
    """Tests for the CoinGeckoProvider class."""

    def test_coingecko_provider_success(self) -> None:
        """Test that CoinGeckoProvider returns price when API succeeds.

        Verifies:
            - Provider correctly parses the CoinGecko API response.
            - Returns the USD price as a float.
        """
        provider = CoinGeckoProvider()
        mock_response = Mock()
        mock_response.json.return_value = {"bitcoin": {"usd": 45000.50}}
        mock_response.raise_for_status = Mock()

        with patch.object(provider.session, "get", return_value=mock_response):
            price = provider.fetch_price("bitcoin")

        assert price == 45000.50

    def test_coingecko_provider_network_error(self) -> None:
        """Test that CoinGeckoProvider returns None on network failure.

        Verifies:
            - Provider handles RequestException gracefully.
            - Returns None instead of raising an exception.
        """
        provider = CoinGeckoProvider()

        with patch.object(
            provider.session,
            "get",
            side_effect=requests.exceptions.RequestException("Connection error"),
        ):
            price = provider.fetch_price("bitcoin")

        assert price is None

    def test_coingecko_batch_fetch(self) -> None:
        """Test that CoinGeckoProvider can fetch multiple symbols in one call.

        Verifies:
            - Batch fetch returns prices for all requested symbols.
            - Missing symbols are excluded from results.
        """
        provider = CoinGeckoProvider()
        mock_response = Mock()
        mock_response.json.return_value = {
            "bitcoin": {"usd": 45000.00},
            "ethereum": {"usd": 3200.00},
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider.session, "get", return_value=mock_response):
            prices = provider.fetch_batch_prices(["bitcoin", "ethereum"])

        assert prices == {"bitcoin": 45000.00, "ethereum": 3200.00}


# ============================================================================
# YahooFinanceProvider Tests
# ============================================================================


class TestYahooFinanceProvider:
    """Tests for the YahooFinanceProvider class."""

    def test_yahoo_provider_success(self) -> None:
        """Test that YahooFinanceProvider returns price when yfinance succeeds.

        Verifies:
            - Provider correctly extracts price from yfinance Ticker.
            - Returns the price as a float.
        """
        provider = YahooFinanceProvider()

        mock_ticker = Mock()
        mock_fast_info = Mock()
        mock_fast_info.last_price = 175.50
        mock_ticker.fast_info = mock_fast_info

        with patch("scripts.sync_prices.yf.Ticker", return_value=mock_ticker):
            price = provider.fetch_price("AAPL")

        assert price == 175.50

    def test_yahoo_provider_failure(self) -> None:
        """Test that YahooFinanceProvider returns None on error.

        Verifies:
            - Provider handles exceptions from yfinance gracefully.
            - Returns None instead of raising an exception.
        """
        provider = YahooFinanceProvider()

        with patch(
            "scripts.sync_prices.yf.Ticker",
            side_effect=Exception("Network error"),
        ):
            price = provider.fetch_price("AAPL")

        assert price is None


# ============================================================================
# PythonTrioAPIClient Tests
# ============================================================================


class TestPythonTrioAPIClient:
    """Tests for the PythonTrioAPIClient class."""

    def test_api_client_fetch_assets(self) -> None:
        """Test that API client can fetch assets list.

        Verifies:
            - Client correctly parses the assets list from API response.
            - Returns list of asset dictionaries.
        """
        client = PythonTrioAPIClient("http://localhost:8000")
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Bitcoin", "symbol": "BTC"},
            {"id": 2, "name": "Ethereum", "symbol": "ETH"},
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            assets = client.fetch_assets()

        assert assets is not None
        assert len(assets) == 2
        assert assets[0]["name"] == "Bitcoin"
        assert assets[1]["name"] == "Ethereum"

    def test_api_client_submit_price(self) -> None:
        """Test that API client can submit a price record.

        Verifies:
            - Client sends correct payload to the API.
            - Returns True on successful submission.
        """
        client = PythonTrioAPIClient("http://localhost:8000")
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": 1, "price": 45000.00}

        with patch.object(client.session, "post", return_value=mock_response) as mock_post:
            recorded_at = datetime(2024, 1, 15, 12, 0, 0)
            result = client.submit_price(
                asset_id=1,
                price=45000.00,
                source="coingecko",
                recorded_at=recorded_at,
            )

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["asset_id"] == 1
        assert call_kwargs[1]["json"]["price"] == 45000.00
        assert call_kwargs[1]["json"]["source"] == "coingecko"


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryWithExponentialBackoff:
    """Tests for the retry_with_exponential_backoff function."""

    def test_retry_with_exponential_backoff_success(self) -> None:
        """Test that retry returns result on first success.

        Verifies:
            - Function returns immediately when first attempt succeeds.
            - No additional retries are performed.
        """
        mock_func = Mock(return_value="success_value")

        with patch("scripts.sync_prices.time.sleep"):
            result = retry_with_exponential_backoff(mock_func, max_retries=3)

        assert result == "success_value"
        assert mock_func.call_count == 1

    def test_retry_with_exponential_backoff_failure(self) -> None:
        """Test that retry returns None after max retries exhausted.

        Verifies:
            - Function attempts the maximum number of retries.
            - Returns None when all attempts fail.
            - Exponential backoff is applied between retries.
        """
        mock_func = Mock(return_value=None)

        with patch("scripts.sync_prices.time.sleep") as mock_sleep:
            result = retry_with_exponential_backoff(mock_func, max_retries=3)

        assert result is None
        assert mock_func.call_count == 3
        # Verify exponential backoff: sleep is called twice (between attempts 1-2 and 2-3)
        assert mock_sleep.call_count == 2


# ============================================================================
# PriceSyncService Tests
# ============================================================================


class TestPriceSyncService:
    """Tests for the PriceSyncService class."""

    def test_sync_service_sync_all_prices(self) -> None:
        """Test that sync service orchestrates full price sync.

        Verifies:
            - Service fetches assets from API.
            - Fetches prices from appropriate providers.
            - Submits prices back to the API.
        """
        mock_api_client = Mock(spec=PythonTrioAPIClient)
        mock_api_client.fetch_assets.return_value = [
            {"id": 1, "name": "Bitcoin", "symbol": "BTC"},
            {"id": 2, "name": "AAPL", "symbol": "AAPL"},
        ]
        mock_api_client.submit_price.return_value = True

        mock_coingecko = Mock()
        mock_coingecko.fetch_price.return_value = 45000.00

        mock_yahoo = Mock()
        mock_yahoo.fetch_price.return_value = 175.50

        service = PriceSyncService(
            api_client=mock_api_client,
            coingecko_provider=mock_coingecko,
            yahoo_provider=mock_yahoo,
        )

        with patch("scripts.sync_prices.time.sleep"):
            service.sync_all_prices()

        # Verify assets were fetched
        mock_api_client.fetch_assets.assert_called()

        # Verify prices were fetched from appropriate providers
        mock_coingecko.fetch_price.assert_called_with("bitcoin")
        mock_yahoo.fetch_price.assert_called_with("AAPL")

        # Verify prices were submitted
        assert mock_api_client.submit_price.call_count == 2

    def test_sync_service_skips_unmapped_assets(self) -> None:
        """Test that sync service ignores assets not in the symbol mapping.

        Verifies:
            - Service skips assets that are not in ASSET_SYMBOL_MAP.
            - No price fetch or submission is attempted for unmapped assets.
        """
        mock_api_client = Mock(spec=PythonTrioAPIClient)
        mock_api_client.fetch_assets.return_value = [
            {"id": 1, "name": "UnknownAsset", "symbol": "UNK"},
            {"id": 2, "name": "AnotherUnknown", "symbol": "XXX"},
        ]

        mock_coingecko = Mock()
        mock_yahoo = Mock()

        service = PriceSyncService(
            api_client=mock_api_client,
            coingecko_provider=mock_coingecko,
            yahoo_provider=mock_yahoo,
        )

        with patch("scripts.sync_prices.time.sleep"):
            service.sync_all_prices()

        # Verify no price fetches were attempted
        mock_coingecko.fetch_price.assert_not_called()
        mock_yahoo.fetch_price.assert_not_called()

        # Verify no price submissions were made
        mock_api_client.submit_price.assert_not_called()
