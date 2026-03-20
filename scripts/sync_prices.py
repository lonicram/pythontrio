"""Price synchronization script entry point.

This script fetches current prices for all registered assets and
updates them via the FastAPI application's /prices/ endpoint.

Designed to run as a scheduled cron job every 10 minutes.

Configuration:
    API_BASE_URL: Base URL of the FastAPI application (default: http://localhost:8000)
    SYNC_TIMEOUT: HTTP timeout in seconds (default: 30)

Example usage:
    python scripts/sync_prices.py
    OR
    python -m scripts.sync_prices

Cron setup (every 10 minutes):
    */10 * * * * cd /path/to/python_trio && ./venv/bin/python scripts/sync_prices.py >> /var/log/price_sync.log 2>&1
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path if running script directly
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from scripts.sync import run_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    asyncio.run(run_sync())
