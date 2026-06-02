"""FastAPI application entry point."""

from fastapi import FastAPI

from app.config import settings
from app.mcp_server import mcp
from app.routers import asset_prices, assets, holdings, onboarding, portfolios, user_profiles

# Create MCP HTTP app first to get its lifespan
mcp_app = mcp.http_app(path="/")

# Pass MCP lifespan to FastAPI (required for MCP session management)
app = FastAPI(title=settings.app_name, lifespan=mcp_app.lifespan)

# REST API routers
app.include_router(user_profiles.router)
app.include_router(portfolios.router)
app.include_router(assets.router)
app.include_router(holdings.router)
app.include_router(asset_prices.router)
app.include_router(onboarding.router)

# MCP endpoint (Streamable HTTP)
app.mount("/mcp", mcp_app)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning a welcome message."""
    return {"message": f"Welcome to {settings.app_name}"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
