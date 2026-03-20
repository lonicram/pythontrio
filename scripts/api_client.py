"""API client functions for interacting with the FastAPI application."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from scripts.config import API_BASE_URL

logger = logging.getLogger(__name__)


async def fetch_assets(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all assets from the API.

    Args:
        client: HTTP client instance.

    Returns:
        List of asset dictionaries.

    Raises:
        httpx.HTTPError: If the request fails.
    """
    response = await client.get(f"{API_BASE_URL}/assets/")
    response.raise_for_status()
    return response.json()


async def record_price(
    client: httpx.AsyncClient,
    asset_id: int,
    price: Decimal,
    asset_type: str,
) -> bool:
    """Record a price via the API.

    Args:
        client: HTTP client instance.
        asset_id: ID of the asset.
        price: Current price.
        asset_type: Type of asset (for source metadata).

    Returns:
        True if successful, False otherwise.
    """
    payload = {
        "asset_id": asset_id,
        "price": str(price),
        "currency": "USD",
        "source": f"sync_{asset_type}",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = await client.post(f"{API_BASE_URL}/prices/", json=payload)
        response.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.error(f"Failed to record price for asset {asset_id}: {e}")
        return False
