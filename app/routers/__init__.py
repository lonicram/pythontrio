"""API routers."""

from app.routers.assets import router as assets_router
from app.routers.portfolios import router as portfolios_router
from app.routers.prices import router as prices_router

__all__ = ["assets_router", "portfolios_router", "prices_router"]
