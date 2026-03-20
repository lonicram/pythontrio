"""Tests for sync orchestration logic."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from scripts.config import API_BASE_URL, SYNC_TIMEOUT
from scripts.providers import PROVIDER_REGISTRY
from scripts.sync import run_sync, sync_asset_price


@pytest.mark.asyncio
class TestSyncOrchestration:
    """Test suite for sync orchestration functions."""

    @respx.mock
    async def test_sync_asset_price_crypto_success(self):
        """Test successful crypto asset price sync."""
        asset = {
            "id": 1,
            "name": "Bitcoin",
            "code": "BTC",
            "type": "crypto",
        }

        # Mock CoinGecko response
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json={"bitcoin": {"usd": 67234.5}})
        )

        # Mock price recording
        respx.post("http://localhost:8000/prices/").mock(
            return_value=httpx.Response(201, json={})
        )

        async with httpx.AsyncClient() as client:
            name, success, error = await sync_asset_price(client, asset)

        assert name == "Bitcoin"
        assert success is True
        assert error is None

    @respx.mock
    async def test_sync_asset_price_stock_success(self):
        """Test successful stock asset price sync."""
        asset = {
            "id": 2,
            "name": "Apple Inc.",
            "code": "AAPL",
            "type": "stock",
        }

        # Mock yfinance
        with patch("scripts.providers.yfinance_provider.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = {"regularMarketPrice": 178.25}
            mock_ticker.return_value = mock_instance

            # Mock price recording
            respx.post("http://localhost:8000/prices/").mock(
                return_value=httpx.Response(201, json={})
            )

            async with httpx.AsyncClient() as client:
                name, success, error = await sync_asset_price(client, asset)

        assert name == "Apple Inc."
        assert success is True
        assert error is None

    async def test_sync_asset_price_unknown_type(self):
        """Test handling of unknown asset types."""
        asset = {
            "id": 3,
            "name": "Unknown Asset",
            "code": "UNKNOWN",
            "type": "forex",
        }

        async with httpx.AsyncClient() as client:
            name, success, error = await sync_asset_price(client, asset)

        assert name == "Unknown Asset"
        assert success is False
        assert "Unknown asset type" in error

    @respx.mock
    async def test_sync_asset_price_no_price_available(self):
        """Test handling when provider returns None."""
        asset = {
            "id": 1,
            "name": "Unknown Crypto",
            "code": "UNKNOWNCOIN",
            "type": "crypto",
        }

        async with httpx.AsyncClient() as client:
            name, success, error = await sync_asset_price(client, asset)

        assert name == "Unknown Crypto"
        assert success is False
        assert "No price available" in error

    @respx.mock
    async def test_sync_asset_price_recording_fails(self):
        """Test handling when price fetch succeeds but recording fails."""
        asset = {
            "id": 1,
            "name": "Bitcoin",
            "code": "BTC",
            "type": "crypto",
        }

        # Mock successful price fetch
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json={"bitcoin": {"usd": 67234.5}})
        )

        # Mock failed recording
        respx.post("http://localhost:8000/prices/").mock(
            return_value=httpx.Response(500, json={"detail": "Internal error"})
        )

        async with httpx.AsyncClient() as client:
            name, success, error = await sync_asset_price(client, asset)

        assert name == "Bitcoin"
        assert success is False
        assert "Failed to record price" in error

    @respx.mock
    async def test_run_sync_success(self):
        """Test full sync process with successful assets."""
        # Mock /assets/ endpoint
        respx.get("http://localhost:8000/assets/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 1,
                        "name": "Bitcoin",
                        "code": "BTC",
                        "type": "crypto",
                    }
                ],
            )
        )

        # Mock CoinGecko
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json={"bitcoin": {"usd": 67234.5}})
        )

        # Mock price recording
        respx.post("http://localhost:8000/prices/").mock(
            return_value=httpx.Response(201, json={})
        )

        # Run sync - should complete without exceptions
        await run_sync()

    @respx.mock
    async def test_run_sync_empty_assets(self):
        """Test sync with no assets."""
        # Mock empty asset list
        respx.get("http://localhost:8000/assets/").mock(
            return_value=httpx.Response(200, json=[])
        )

        # Should complete without error
        await run_sync()

    @respx.mock
    async def test_run_sync_fetch_assets_fails(self):
        """Test handling when asset fetching fails."""
        # Mock API error
        respx.get("http://localhost:8000/assets/").mock(
            return_value=httpx.Response(500, json={"detail": "Server error"})
        )

        # Should handle gracefully and return (not raise)
        await run_sync()

    @respx.mock
    async def test_run_sync_mixed_success_and_failure(self):
        """Test sync with some successes and some failures."""
        # Mock assets with different types
        respx.get("http://localhost:8000/assets/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": 1, "name": "Bitcoin", "code": "BTC", "type": "crypto"},
                    {"id": 2, "name": "Unknown", "code": "XYZ", "type": "forex"},
                ],
            )
        )

        # Mock successful crypto fetch
        respx.get("https://api.coingecko.com/api/v3/simple/price").mock(
            return_value=httpx.Response(200, json={"bitcoin": {"usd": 67234.5}})
        )

        # Mock price recording
        respx.post("http://localhost:8000/prices/").mock(
            return_value=httpx.Response(201, json={})
        )

        # Should handle mixed results gracefully
        await run_sync()


@pytest.mark.asyncio
class TestConfiguration:
    """Test suite for configuration and registry."""

    def test_provider_registry_contains_expected_types(self):
        """Test that provider registry has expected asset types."""
        assert "crypto" in PROVIDER_REGISTRY
        assert "stock" in PROVIDER_REGISTRY

    def test_provider_registry_providers_are_valid(self):
        """Test that registered providers implement the interface."""
        for _asset_type, provider in PROVIDER_REGISTRY.items():
            assert hasattr(provider, "get_price")
            assert callable(provider.get_price)

    def test_configuration_defaults(self):
        """Test default configuration values."""
        assert API_BASE_URL is not None
        assert SYNC_TIMEOUT > 0
