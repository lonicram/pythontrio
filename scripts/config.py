"""Configuration for price synchronization scripts."""

import os

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SYNC_TIMEOUT = float(os.getenv("SYNC_TIMEOUT", "30"))
