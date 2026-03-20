"""Unit tests for YFinanceProvider."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scripts.providers.yfinance_provider import YFinanceProvider


@pytest.mark.asyncio
class TestYFinanceProvider:
    """Test suite for YFinanceProvider."""

    async def test_get_price_success_regular_market(self, mock_yfinance_info):
        """Test successful price fetch using regularMarketPrice.

        Args:
            mock_yfinance_info: Fixture with mock ticker info.
        """
        provider = YFinanceProvider()

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_yfinance_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("AAPL")

            assert price is not None
            assert isinstance(price, Decimal)
            assert price == Decimal("178.25")
            mock_ticker.assert_called_once_with("AAPL")

    async def test_get_price_success_current_price(self):
        """Test successful price fetch using currentPrice fallback."""
        provider = YFinanceProvider()

        mock_info = {
            "currentPrice": 156.78,
            "symbol": "GOOGL",
        }

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("GOOGL")

            assert price == Decimal("156.78")

    async def test_get_price_multiple_stocks(self):
        """Test fetching prices for different stocks."""
        provider = YFinanceProvider()

        test_cases = [
            ("AAPL", 178.25),
            ("MSFT", 415.50),
            ("GOOGL", 143.75),
            ("TSLA", 185.30),
        ]

        for symbol, expected_price in test_cases:
            mock_info = {
                "regularMarketPrice": expected_price,
                "symbol": symbol,
            }

            with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
                mock_instance = MagicMock()
                mock_instance.info = mock_info
                mock_ticker.return_value = mock_instance

                price = await provider.get_price(symbol)
                assert price == Decimal(str(expected_price))

    async def test_get_price_no_price_data(self):
        """Test handling when no price data is available."""
        provider = YFinanceProvider()

        # Both price fields are None
        mock_info = {
            "symbol": "INVALID",
        }

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("INVALID")
            assert price is None

    async def test_get_price_empty_info(self):
        """Test handling of empty info dictionary."""
        provider = YFinanceProvider()

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = {}
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("INVALID")
            assert price is None

    async def test_get_price_yfinance_exception(self):
        """Test handling of yfinance exceptions."""
        provider = YFinanceProvider()

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("yfinance error")

            price = await provider.get_price("AAPL")
            assert price is None

    async def test_get_price_info_access_error(self):
        """Test handling when accessing .info raises an error."""
        provider = YFinanceProvider()

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = property(
                lambda self: (_ for _ in ()).throw(Exception("Info error"))
            )
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("AAPL")
            assert price is None

    async def test_get_price_zero_price(self):
        """Test handling of zero price (delisted/suspended stocks)."""
        provider = YFinanceProvider()

        mock_info = {
            "regularMarketPrice": 0,
            "currentPrice": 0,
        }

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("DELISTED")
            # Zero is falsy but should still return Decimal("0")
            assert price == Decimal("0")

    async def test_get_price_negative_price(self):
        """Test handling of negative prices (edge case)."""
        provider = YFinanceProvider()

        mock_info = {
            "regularMarketPrice": -10.5,
        }

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("NEGATIVE")
            assert price == Decimal("-10.5")

    async def test_get_price_very_large_number(self):
        """Test handling of very large price numbers."""
        provider = YFinanceProvider()

        mock_info = {
            "regularMarketPrice": 999999.99,
        }

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("EXPENSIVE")
            assert price == Decimal("999999.99")

    async def test_get_price_very_small_number(self):
        """Test handling of very small price numbers (penny stocks)."""
        provider = YFinanceProvider()

        mock_info = {
            "regularMarketPrice": 0.0001,
        }

        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            price = await provider.get_price("PENNY")
            assert price == Decimal("0.0001")
