"""Abstract base class for price providers."""

from abc import ABC, abstractmethod
from decimal import Decimal


class PriceProvider(ABC):
    """Abstract base class for price data providers.

    This interface allows for flexible implementation of different
    price sources (CoinGecko, Yahoo Finance, etc.) while maintaining
    a consistent API for the sync script.
    """

    @abstractmethod
    async def get_price(self, code: str) -> Decimal | None:
        """Fetch the current price for a given asset code.

        Args:
            code: The asset ticker symbol (e.g., "BTC", "AAPL").

        Returns:
            The current price as a Decimal, or None if unavailable.

        Raises:
            This method should not raise exceptions - return None on error.
        """
        pass
