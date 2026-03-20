"""Unit tests for CoinGeckoProvider."""

from decimal import Decimal

import httpx
import pytest
import respx

from scripts.providers.coingecko import CoinGeckoProvider


@pytest.mark.asyncio
class TestCoinGeckoProvider:
    """Test suite for CoinGeckoProvider."""

    @respx.mock
    async def test_get_price_success(self, mock_coingecko_response):
        """Test successful price fetch from CoinGecko.

        Args:
            mock_coingecko_response: Fixture with mock response data.
        """
        provider = CoinGeckoProvider()

        # Mock the CoinGecko API response
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json=mock_coingecko_response)
        )

        price = await provider.get_price("BTC")

        assert price is not None
        assert isinstance(price, Decimal)
        assert price == Decimal("67234.5")

    @respx.mock
    async def test_get_price_case_insensitive(self):
        """Test that ticker codes are case-insensitive."""
        provider = CoinGeckoProvider()

        mock_response = {"ethereum": {"usd": 3456.78}}
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Test lowercase
        price_lower = await provider.get_price("eth")
        assert price_lower == Decimal("3456.78")

        # Test uppercase
        price_upper = await provider.get_price("ETH")
        assert price_upper == Decimal("3456.78")

        # Test mixed case
        price_mixed = await provider.get_price("EtH")
        assert price_mixed == Decimal("3456.78")

    @respx.mock
    async def test_get_price_multiple_coins(self):
        """Test fetching prices for different cryptocurrencies."""
        provider = CoinGeckoProvider()

        test_cases = [
            ("BTC", "bitcoin", 67234.5),
            ("ETH", "ethereum", 3456.78),
            ("SOL", "solana", 123.45),
            ("ADA", "cardano", 0.65),
        ]

        for code, coin_id, expected_price in test_cases:
            mock_response = {coin_id: {"usd": expected_price}}
            respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
                return_value=httpx.Response(200, json=mock_response)
            )

            price = await provider.get_price(code)
            assert price == Decimal(str(expected_price))

    async def test_get_price_unknown_coin(self):
        """Test handling of unknown cryptocurrency codes."""
        provider = CoinGeckoProvider()

        # Unknown coin should return None
        price = await provider.get_price("UNKNOWNCOIN")
        assert price is None

    @respx.mock
    async def test_get_price_api_error(self):
        """Test handling of API errors."""
        provider = CoinGeckoProvider()

        # Mock HTTP error
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )

        price = await provider.get_price("BTC")
        assert price is None

    @respx.mock
    async def test_get_price_rate_limit(self):
        """Test handling of rate limiting (429 status)."""
        provider = CoinGeckoProvider()

        # Mock rate limit response
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
        )

        price = await provider.get_price("BTC")
        assert price is None

    @respx.mock
    async def test_get_price_malformed_response(self):
        """Test handling of malformed API responses."""
        provider = CoinGeckoProvider()

        # Response missing expected fields
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json={"bitcoin": {}})
        )

        price = await provider.get_price("BTC")
        assert price is None

    @respx.mock
    async def test_get_price_network_timeout(self):
        """Test handling of network timeouts."""
        provider = CoinGeckoProvider()

        # Mock timeout
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        price = await provider.get_price("BTC")
        assert price is None

    @respx.mock
    async def test_get_price_invalid_json(self):
        """Test handling of invalid JSON responses."""
        provider = CoinGeckoProvider()

        # Mock invalid JSON
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, text="<html>Not JSON</html>")
        )

        price = await provider.get_price("BTC")
        assert price is None

    @respx.mock
    async def test_get_price_empty_response(self):
        """Test handling of empty response."""
        provider = CoinGeckoProvider()

        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json={})
        )

        price = await provider.get_price("BTC")
        assert price is None

    def test_symbol_to_id_mapping(self):
        """Test that common cryptocurrencies are mapped correctly."""
        provider = CoinGeckoProvider()

        expected_mappings = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
            "BNB": "binancecoin",
            "SOL": "solana",
            "USDC": "usd-coin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
        }

        for symbol, expected_id in expected_mappings.items():
            assert provider.SYMBOL_TO_ID[symbol] == expected_id
