"""Price synchronization orchestration logic."""

import logging

import httpx

from scripts.api_client import fetch_assets, record_price
from scripts.config import API_BASE_URL, SYNC_TIMEOUT
from scripts.providers import PROVIDER_REGISTRY

logger = logging.getLogger(__name__)


async def sync_asset_price(
    client: httpx.AsyncClient, asset: dict
) -> tuple[str, bool, str | None]:
    """Sync price for a single asset.

    Args:
        client: HTTP client instance.
        asset: Asset dictionary with id, name, code, type.

    Returns:
        Tuple of (asset_name, success, error_message).
    """
    asset_id = asset["id"]
    asset_name = asset["name"]
    asset_code = asset["code"]
    asset_type = asset["type"]

    # Get the appropriate provider for this asset type
    provider = PROVIDER_REGISTRY.get(asset_type.lower())
    if not provider:
        logger.warning(
            f"No provider for asset type '{asset_type}' (asset: {asset_name})"
        )
        return (asset_name, False, f"Unknown asset type: {asset_type}")

    # Fetch price from provider
    try:
        price = await provider.get_price(asset_code)
    except Exception as e:
        logger.error(f"Unexpected error fetching price for {asset_name}: {e}")
        return (asset_name, False, f"Provider error: {e}")

    if price is None:
        logger.warning(f"No price available for {asset_name} ({asset_code})")
        return (asset_name, False, "No price available")

    # Record the price via API
    success = await record_price(client, asset_id, price, asset_type)

    if success:
        logger.info(f"✓ {asset_name} ({asset_code}): ${price}")
        return (asset_name, True, None)

    return (asset_name, False, "Failed to record price")


async def run_sync() -> None:
    """Run the price synchronization process.

    This is the main orchestration function that:
    1. Fetches all assets from the API
    2. Syncs prices for each asset
    3. Logs summary statistics
    """
    logger.info("=" * 60)
    logger.info("Starting price sync")
    logger.info(f"API Base URL: {API_BASE_URL}")
    logger.info("=" * 60)

    success_count = 0
    failure_count = 0
    failures = []

    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            # Fetch all assets
            logger.info("Fetching assets...")
            try:
                assets = await fetch_assets(client)
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch assets: {e}")
                logger.error("Aborting sync")
                return

            if not assets:
                logger.info("No assets found. Nothing to sync.")
                return

            logger.info(f"Found {len(assets)} asset(s) to sync")
            logger.info("-" * 60)

            # Sync each asset
            for asset in assets:
                asset_name, success, error = await sync_asset_price(client, asset)

                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    failures.append((asset_name, error))

    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}")
        raise

    # Print summary
    logger.info("-" * 60)
    logger.info("Sync complete")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")

    if failures:
        logger.warning("Failed assets:")
        for asset_name, error in failures:
            logger.warning(f"  - {asset_name}: {error}")

    logger.info("=" * 60)
