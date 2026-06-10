"""MCP server for PythonTrio portfolio management.

Exposes read-only tools via Streamable HTTP transport.
Mount on FastAPI app with: app.mount("/mcp", mcp.http_app())
"""

from fastmcp import FastMCP

from app.database import SessionLocal
from app.schemas import (
    AssetResponse,
    PortfolioResponse,
    PortfolioWithHoldingsResponse,
    UserProfileResponse,
)
from app.services.read_service import ReadService

# Initialize FastMCP server
mcp = FastMCP(
    name="PythonTrio Portfolio",
    instructions="""
    You have access to a portfolio management system. Use these tools to:
    - List available assets (cryptocurrencies, stocks, ETFs)
    - View user portfolios and their holdings
    - Look up user profiles

    All monetary values use Decimal precision for financial accuracy.
    """,
)


@mcp.tool()
def list_assets() -> list[AssetResponse]:
    """List all available assets in the portfolio system.

    Returns a list of assets including their symbol, name, type, and current price.
    Useful for seeing what assets are available for portfolio management.
    """
    db = SessionLocal()
    try:
        service = ReadService(db)
        return [AssetResponse.model_validate(a) for a in service.list_assets()]
    finally:
        db.close()


@mcp.tool()
def list_portfolios(
    include_holdings: bool = False,
) -> list[PortfolioResponse] | list[PortfolioWithHoldingsResponse]:
    """List all portfolios in the system.

    Args:
        include_holdings: If True, include the holdings for each portfolio.

    Returns a list of portfolios with their names, descriptions, and optionally
    their holdings (assets and quantities).
    """
    db = SessionLocal()
    try:
        service = ReadService(db)
        portfolios = service.list_portfolios(include_holdings=include_holdings)

        if include_holdings:
            return [PortfolioWithHoldingsResponse.model_validate(p) for p in portfolios]
        return [PortfolioResponse.model_validate(p) for p in portfolios]
    finally:
        db.close()


@mcp.tool()
def list_users(active_only: bool = True) -> list[UserProfileResponse]:
    """List user profiles in the system.

    Args:
        active_only: If True (default), only return active users.

    Returns a list of users with their email, username, and full name.
    """
    db = SessionLocal()
    try:
        service = ReadService(db)
        return [
            UserProfileResponse.model_validate(u)
            for u in service.list_users(active_only=active_only)
        ]
    finally:
        db.close()


# For standalone execution (stdio mode for local testing)
if __name__ == "__main__":
    mcp.run()
