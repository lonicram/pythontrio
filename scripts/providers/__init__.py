"""Price provider implementations."""

from scripts.providers.base import PriceProvider
from scripts.providers.coingecko import CoinGeckoProvider
from scripts.providers.yfinance_provider import YFinanceProvider

# Registry mapping asset types to their price providers
PROVIDER_REGISTRY: dict[str, PriceProvider] = {
    "crypto": CoinGeckoProvider(),
    "stock": YFinanceProvider(),
}

__all__ = [
    "PriceProvider",
    "CoinGeckoProvider",
    "YFinanceProvider",
    "PROVIDER_REGISTRY",
]
