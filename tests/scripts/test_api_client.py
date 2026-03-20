"""Tests for API client functions."""

from decimal import Decimal

import httpx
import pytest
import respx

from scripts.api_client import fetch_assets, record_price


@pytest.mark.asyncio
class TestAPIClient:
    """Test suite for API client functions."""

    @respx.mock
    async def test_fetch_assets_success(self, mock_assets):
        """Test successful asset fetching.

        Args:
            mock_assets: Fixture with sample asset data.
        """
        # Mock the /assets/ endpoint
        respx.get("http://localhost:8000/assets/").mock(
            return_value=httpx.Response(200, json=mock_assets)
        )

        async with httpx.AsyncClient() as client:
            assets = await fetch_assets(client)

        assert len(assets) == 3
        assert assets[0]["name"] == "Bitcoin"
        assert assets[1]["code"] == "AAPL"

    @respx.mock
    async def test_fetch_assets_api_error(self):
        """Test handling of API errors when fetching assets."""
        # Mock API error
        respx.get("http://localhost:8000/assets/").mock(
            return_value=httpx.Response(500, json={"detail": "Server error"})
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_assets(client)

    @respx.mock
    async def test_record_price_success(self):
        """Test successful price recording."""
        # Mock the /prices/ endpoint
        respx.post("http://localhost:8000/prices/").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": 1,
                    "asset_id": 1,
                    "price": "67234.5",
                    "currency": "USD",
                    "source": "sync_crypto",
                    "recorded_at": "2024-03-20T10:00:00Z",
                    "created_at": "2024-03-20T10:00:00Z",
                },
            )
        )

        async with httpx.AsyncClient() as client:
            success = await record_price(
                client, asset_id=1, price=Decimal("67234.5"), asset_type="crypto"
            )

        assert success is True

    @respx.mock
    async def test_record_price_failure(self):
        """Test handling of price recording failures."""
        # Mock API error
        respx.post("http://localhost:8000/prices/").mock(
            return_value=httpx.Response(404, json={"detail": "Asset not found"})
        )

        async with httpx.AsyncClient() as client:
            success = await record_price(
                client, asset_id=999, price=Decimal("100.0"), asset_type="stock"
            )

        assert success is False
