"""Pytest fixtures for price sync script tests."""

import pytest


@pytest.fixture
def mock_assets():
    """Sample asset data for price sync testing.

    Returns:
        List of mock asset dictionaries.
    """
    return [
        {
            "id": 1,
            "name": "Bitcoin",
            "code": "BTC",
            "type": "crypto",
            "price": None,
            "portfolio_id": 1,
        },
        {
            "id": 2,
            "name": "Apple Inc.",
            "code": "AAPL",
            "type": "stock",
            "price": None,
            "portfolio_id": 1,
        },
        {
            "id": 3,
            "name": "Unknown Asset",
            "code": "UNKNOWN",
            "type": "forex",
            "price": None,
            "portfolio_id": 1,
        },
    ]


@pytest.fixture
def mock_coingecko_response():
    """Mock successful CoinGecko API response.

    Returns:
        Dict simulating CoinGecko API response.
    """
    return {"bitcoin": {"usd": 67234.5}}


@pytest.fixture
def mock_yfinance_info():
    """Mock successful yfinance ticker info.

    Returns:
        Dict simulating yfinance ticker.info response.
    """
    return {
        "regularMarketPrice": 178.25,
        "currentPrice": 178.25,
        "symbol": "AAPL",
    }
