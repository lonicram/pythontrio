"""CoinGecko price provider for cryptocurrency prices."""

import logging
from decimal import Decimal

import httpx

from scripts.providers.base import PriceProvider

logger = logging.getLogger(__name__)

# Constants
API_TIMEOUT = 30.0
CURRENCY = "usd"


class CoinGeckoProvider(PriceProvider):
    """Fetches cryptocurrency prices from the CoinGecko public API.

    CoinGecko provides a free API without requiring authentication.
    This provider maps common ticker symbols to CoinGecko's coin IDs.
    """

    # Mapping from common ticker symbols to CoinGecko coin IDs
    SYMBOL_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDT": "tether",
        "BNB": "binancecoin",
        "SOL": "solana",
        "USDC": "usd-coin",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "TRX": "tron",
        "AVAX": "avalanche-2",
        "MATIC": "matic-network",
        "DOT": "polkadot",
        "LTC": "litecoin",
        "LINK": "chainlink",
    }

    BASE_URL = "https://api.coingecko.com/api/v3/simple/price"

    async def get_price(self, code: str) -> Decimal | None:
        """Fetch current price from CoinGecko.

        Args:
            code: Cryptocurrency ticker symbol (e.g., "BTC", "ETH").

        Returns:
            Current USD price as Decimal, or None if unavailable.
        """
        # Normalize code to uppercase
        code = code.upper()

        # Get CoinGecko coin ID
        coin_id = self.SYMBOL_TO_ID.get(code)
        if not coin_id:
            logger.warning(f"Unknown cryptocurrency code: {code}")
            return None

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={"ids": coin_id, "vs_currencies": CURRENCY},
                )
                response.raise_for_status()

                data = response.json()
                if coin_id in data and CURRENCY in data[coin_id]:
                    price = data[coin_id][CURRENCY]
                    return Decimal(str(price))
                else:
                    logger.warning(f"No price data returned for {code} ({coin_id})")
                    return None

        except httpx.HTTPError:
            logger.exception(f"HTTP error fetching {code} from CoinGecko")
            return None
        except (KeyError, ValueError, TypeError):
            logger.exception(f"Error parsing CoinGecko response for {code}")
            return None
        except Exception:
            logger.exception(f"Unexpected error fetching {code} from CoinGecko")
            return None
