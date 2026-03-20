"""Yahoo Finance price provider for stock prices."""

import logging
from decimal import Decimal

import yfinance as yf

from scripts.providers.base import PriceProvider

logger = logging.getLogger(__name__)

# Constants
REGULAR_MARKET_PRICE_KEY = "regularMarketPrice"
CURRENT_PRICE_KEY = "currentPrice"


class YFinanceProvider(PriceProvider):
    """Fetches stock prices using the yfinance library.

    yfinance wraps Yahoo Finance's API and provides free access
    to stock market data without requiring authentication.
    """

    async def get_price(self, code: str) -> Decimal | None:
        """Fetch current stock price from Yahoo Finance.

        Args:
            code: Stock ticker symbol (e.g., "AAPL", "GOOGL").

        Returns:
            Current market price as Decimal, or None if unavailable.
        """
        try:
            ticker = yf.Ticker(code)
            info = ticker.info

            # Try to get the regular market price, fallback to current price
            price = info.get(REGULAR_MARKET_PRICE_KEY) or info.get(CURRENT_PRICE_KEY)

            if price is None:
                logger.warning(f"No price data available for {code}")
                return None

            return Decimal(str(price))

        except Exception:
            logger.exception(f"Error fetching price for {code} from Yahoo Finance")
            return None
