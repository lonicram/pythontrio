# MCP Integration with FastMCP - Read-Only Tools (Web API)

**Scope:** Read-only MCP tools for listing assets, portfolios, and users, deployed as a web API via Streamable HTTP transport.

---

## 1. Overview

This plan adds Model Context Protocol (MCP) support to PythonTrio using FastMCP, deployed as a **web API** accessible by Claude, Cursor, and other MCP-compatible clients over HTTP. The MCP server is mounted on the existing FastAPI application at `/mcp`, enabling a single deployment that serves both REST and MCP interfaces.

**Transport:** Streamable HTTP (recommended for web deployment, supersedes HTTP+SSE).

**Initial tools:** `list_assets`, `list_portfolios`, `list_users` (read-only).

**Key design:** Reuse existing Pydantic schemas (with `from_attributes=True`) for ORM-to-JSON serialization, ensuring consistency between REST and MCP responses.

---

## 2. Architecture Decision

### Why Web API (Streamable HTTP) Instead of stdio?

| Aspect | stdio | Streamable HTTP |
|--------|-------|-----------------|
| Deployment | Local only (desktop clients) | Remote accessible (any client) |
| Integration | Claude Desktop launches process | Any HTTP client can connect |
| Scaling | Single user | Multi-user, load balanceable |
| Auth | Inherits OS user permissions | API key / OAuth 2.1 |

**Chosen approach:** Mount FastMCP on the existing FastAPI app (Option C from MCP_INTEGRATION.md). This gives us:
- Single deployment serving REST + MCP
- Shared database connection pool
- Consistent authentication layer
- No additional process management

### Target Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              FastAPI app                    │
   REST clients ───▶│  /assets /portfolios /users ... (routers)  │
                    │                                             │
   MCP clients  ───▶│  /mcp  ─────────────────┐                  │
   (Claude,         │                          │                  │
    Cursor,         │                          ▼                  │
    agents)         │                   ReadService               │
                    │                          │                  │
                    │                          ▼                  │
                    │              SQLAlchemy Session             │
                    └──────────────────────────┬──────────────────┘
                                               ▼
                                          PostgreSQL
```

---

## 3. Implementation Steps

### Step 1: Add Dependencies

**File to modify:** `requirements.txt`

```
fastmcp>=2.0.0
```

> Note: FastMCP 2.x includes Streamable HTTP support. Earlier versions only support stdio.

Install:

```bash
pip install "fastmcp>=2.0.0"
```

---

### Step 2: Extract Pydantic Schemas to Shared Module

Currently, response schemas are defined inline in router files. Extract them to `app/schemas/` for reuse by both REST and MCP.

**File to create:** `app/schemas/responses.py`

```python
"""Shared Pydantic response schemas for REST API and MCP tools."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AssetResponse(BaseModel):
    """Asset response schema."""

    id: int
    symbol: str
    name: str
    asset_type: str
    description: str | None
    price: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    """Portfolio response schema."""

    id: int
    owner_id: int | None
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class HoldingResponse(BaseModel):
    """Portfolio holding response schema."""

    id: int
    asset_id: int
    quantity: Decimal
    purchase_price: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioWithHoldingsResponse(BaseModel):
    """Portfolio with nested holdings."""

    id: int
    owner_id: int | None
    name: str
    description: str | None
    holdings: list[HoldingResponse]

    model_config = {"from_attributes": True}


class UserProfileResponse(BaseModel):
    """User profile response schema."""

    id: int
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
```

**File to modify:** `app/schemas/__init__.py`

```python
"""Pydantic schemas for request/response validation."""

from app.schemas.onboarding import (
    HoldingOut,
    PortfolioOut,
    StarterHolding,
    UserOnboardRequest,
    UserOnboardResponse,
)
from app.schemas.responses import (
    AssetResponse,
    HoldingResponse,
    PortfolioResponse,
    PortfolioWithHoldingsResponse,
    UserProfileResponse,
)

__all__ = [
    # Onboarding
    "HoldingOut",
    "PortfolioOut",
    "StarterHolding",
    "UserOnboardRequest",
    "UserOnboardResponse",
    # Responses (shared)
    "AssetResponse",
    "HoldingResponse",
    "PortfolioResponse",
    "PortfolioWithHoldingsResponse",
    "UserProfileResponse",
]
```

---

### Step 3: Refactor Routers to Use Shared Schemas

Move inline Pydantic response schemas from routers to the shared module and update imports. This ensures REST API and MCP use identical response schemas.

**File to modify:** `app/routers/assets.py`

```python
"""Asset API routes for CRUD operations."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.asset import Asset
from app.schemas import AssetResponse  # <-- Import shared schema

router = APIRouter(prefix="/assets", tags=["assets"])


# Keep Create schema inline (input validation specific to this router)
class AssetCreate(BaseModel):
    """Schema for creating/updating an asset."""

    symbol: str
    name: str
    asset_type: str = "crypto"
    description: str | None = None
    price: Decimal | None = None


# DELETE the inline AssetResponse class - now imported from app.schemas


@router.get("/", response_model=list[AssetResponse])
def list_assets(db: Session = Depends(get_db)) -> list[AssetResponse]:
    """List all assets in the catalog."""
    return db.query(Asset).all()


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)) -> AssetResponse:
    """Get an asset by ID."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/", response_model=AssetResponse, status_code=201)
def create_asset(data: AssetCreate, db: Session = Depends(get_db)) -> AssetResponse:
    """Create a new asset in the catalog."""
    asset = Asset(**data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int, data: AssetCreate, db: Session = Depends(get_db)
) -> AssetResponse:
    """Update an asset."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for key, value in data.model_dump().items():
        setattr(asset, key, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an asset from the catalog."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()
```

---

**File to modify:** `app/routers/portfolios.py`

```python
"""Portfolio API routes for CRUD operations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.portfolio import Portfolio
from app.schemas import PortfolioResponse  # <-- Import shared schema

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


# Keep Create schema inline
class PortfolioCreate(BaseModel):
    """Schema for creating/updating a portfolio."""

    name: str
    description: str | None = None
    owner_id: int | None = None


# DELETE the inline PortfolioResponse class


@router.get("/", response_model=list[PortfolioResponse])
def list_portfolios(db: Session = Depends(get_db)):
    return db.query(Portfolio).all()


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.post("/", response_model=PortfolioResponse, status_code=201)
def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db)):
    portfolio = Portfolio(**data.model_dump())
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: int, data: PortfolioCreate, db: Session = Depends(get_db)
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    for key, value in data.model_dump().items():
        setattr(portfolio, key, value)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()
```

---

**File to modify:** `app/routers/user_profiles.py`

```python
"""UserProfile API routes for CRUD operations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas import UserProfileResponse  # <-- Import shared schema

router = APIRouter(prefix="/user-profiles", tags=["user-profiles"])


# Keep Create/Update schemas inline (input validation)
class UserProfileCreate(BaseModel):
    """Schema for creating a new user profile."""

    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    is_active: bool = True


class UserProfileUpdate(BaseModel):
    """Schema for updating an existing user profile."""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


# DELETE the inline UserProfileResponse class


@router.get("/", response_model=list[UserProfileResponse])
def list_user_profiles(db: Session = Depends(get_db)) -> list[UserProfileResponse]:
    """List all user profiles."""
    return db.query(UserProfile).all()


# ... rest of router unchanged (uses UserProfileResponse from import)
```

---

**File to modify:** `app/routers/holdings.py`

```python
"""Holdings API routes."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.portfolio_holding import PortfolioHolding
from app.schemas import HoldingResponse  # <-- Import shared schema

router = APIRouter(prefix="/portfolios", tags=["holdings"])


# Keep Create/Update schemas inline
class HoldingCreate(BaseModel):
    """Schema for adding a holding to a portfolio."""

    asset_id: int
    quantity: Decimal
    purchase_price: Decimal | None = None


class HoldingUpdate(BaseModel):
    """Schema for updating a holding."""

    quantity: Decimal | None = None
    purchase_price: Decimal | None = None


# Keep AssetInfo inline (nested in holding response, specific to this router)
class AssetInfo(BaseModel):
    """Nested asset info in holding response."""

    id: int
    symbol: str
    name: str
    price: Decimal | None

    model_config = {"from_attributes": True}


# Extend shared HoldingResponse with nested asset
class HoldingWithAssetResponse(HoldingResponse):
    """Holding response with nested asset details."""

    asset: AssetInfo


# DELETE the inline HoldingResponse class


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingWithAssetResponse])
def list_holdings(portfolio_id: int, db: Session = Depends(get_db)):
    # ... implementation unchanged
```

---

### Refactor Summary

| Router | Remove Inline Class | Import From `app.schemas` |
|--------|---------------------|---------------------------|
| `assets.py` | `AssetResponse` | `AssetResponse` |
| `portfolios.py` | `PortfolioResponse` | `PortfolioResponse` |
| `user_profiles.py` | `UserProfileResponse` | `UserProfileResponse` |
| `holdings.py` | `HoldingResponse` | `HoldingResponse` |

**Keep inline:** `*Create`, `*Update` schemas remain in routers (input validation specific to each endpoint).

**Benefit:** Single source of truth for response shapes, shared between REST and MCP.

---

### Step 4: Create ReadService

**File to create:** `app/services/read_service.py`

```python
"""Read-only service for querying portfolio data."""

from sqlalchemy.orm import Session, joinedload

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.user_profile import UserProfile


class ReadService:
    """Service for read-only database queries.

    Following project conventions:
    - Session is injected via constructor
    - No commits (caller controls transaction, though reads don't require it)
    - Returns ORM models; caller handles serialization
    """

    def __init__(self, db: Session):
        """Initialize with database session.

        Args:
            db: SQLAlchemy session for database queries.
        """
        self.db = db

    def list_assets(self) -> list[Asset]:
        """Retrieve all assets.

        Returns:
            List of Asset models ordered by symbol.
        """
        return self.db.query(Asset).order_by(Asset.symbol).all()

    def list_portfolios(self, include_holdings: bool = False) -> list[Portfolio]:
        """Retrieve all portfolios.

        Args:
            include_holdings: If True, eagerly load holdings relationship.

        Returns:
            List of Portfolio models ordered by name.
        """
        query = self.db.query(Portfolio)
        if include_holdings:
            query = query.options(joinedload(Portfolio.holdings))
        return query.order_by(Portfolio.name).all()

    def list_users(self, active_only: bool = True) -> list[UserProfile]:
        """Retrieve user profiles.

        Args:
            active_only: If True, only return active users.

        Returns:
            List of UserProfile models ordered by email.
        """
        query = self.db.query(UserProfile)
        if active_only:
            query = query.filter(UserProfile.is_active == True)  # noqa: E712
        return query.order_by(UserProfile.email).all()
```

---

### Step 5: Create MCP Server Module

**File to create:** `app/mcp_server.py`

```python
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
def list_assets() -> list[dict]:
    """List all available assets in the portfolio system.

    Returns a list of assets including their symbol, name, type, and current price.
    Useful for seeing what assets are available for portfolio management.
    """
    db = SessionLocal()
    try:
        service = ReadService(db)
        assets = service.list_assets()
        # Use Pydantic for consistent serialization with REST API
        return [
            AssetResponse.model_validate(a).model_dump(mode="json")
            for a in assets
        ]
    finally:
        db.close()


@mcp.tool()
def list_portfolios(include_holdings: bool = False) -> list[dict]:
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
            return [
                PortfolioWithHoldingsResponse.model_validate(p).model_dump(mode="json")
                for p in portfolios
            ]
        return [
            PortfolioResponse.model_validate(p).model_dump(mode="json")
            for p in portfolios
        ]
    finally:
        db.close()


@mcp.tool()
def list_users(active_only: bool = True) -> list[dict]:
    """List user profiles in the system.

    Args:
        active_only: If True (default), only return active users.

    Returns a list of users with their email, username, and full name.
    """
    db = SessionLocal()
    try:
        service = ReadService(db)
        users = service.list_users(active_only=active_only)
        return [
            UserProfileResponse.model_validate(u).model_dump(mode="json")
            for u in users
        ]
    finally:
        db.close()


# For standalone execution (stdio mode for local testing)
if __name__ == "__main__":
    mcp.run()
```

**Key Pydantic usage:**
- `model_validate(orm_obj)` - converts SQLAlchemy model to Pydantic model
- `model_dump(mode="json")` - serializes to JSON-safe dict (handles Decimal, datetime)
- Same schemas used by REST API ensures consistent response format

---

### Step 6: Mount MCP on FastAPI

**File to modify:** `app/main.py`

**IMPORTANT:** FastMCP requires its lifespan to be passed to the parent FastAPI application. Without this, the MCP session manager won't initialize and you'll get runtime errors.

**Key steps:**
1. Create the MCP HTTP app first with `http_app(path="/")`
2. Pass its lifespan to the FastAPI constructor
3. Mount the MCP app at `/mcp`

```python
from app.mcp_server import mcp

# Create MCP HTTP app first to get its lifespan
mcp_app = mcp.http_app(path="/")

# Pass MCP lifespan to FastAPI (required for MCP session management)
app = FastAPI(title=settings.app_name, lifespan=mcp_app.lifespan)

# Mount MCP at /mcp endpoint
app.mount("/mcp", mcp_app)
```

**Full example of modified main.py:**

```python
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
```

**Why `path="/"`?**

The `http_app()` method creates a Starlette app with its own routes. By default it creates a route at `/mcp`. When mounted at `/mcp`, this would result in `/mcp/mcp`. Setting `path="/"` makes the route accessible directly at the mount point.

---

### Step 7: Add Makefile Targets

**File to modify:** `Makefile`

```makefile
.PHONY: serve mcp-local

# Run FastAPI server (serves both REST and MCP)
serve:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run MCP server standalone (stdio mode for local testing)
mcp-local:
	python -m app.mcp_server
```

---

## 4. MCP Endpoints

Once deployed, your MCP server is available at:

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:8000/mcp/` | MCP Streamable HTTP endpoint (note trailing slash) |

### Protocol Flow

MCP uses JSON-RPC 2.0 over HTTP with session management:

**1. Initialize session:**
```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}'
```

Response includes `mcp-session-id` header - save this for subsequent requests.

**2. List tools (with session ID):**
```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <session-id-from-initialize>" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}'
```

**3. Call a tool:**
```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <session-id>" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_assets", "arguments": {}}, "id": 3}'
```

### Required Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| `Accept` | `application/json, text/event-stream` | Yes |
| `mcp-session-id` | Session ID from initialize | After initialize |

---

## 5. Client Integration

### Claude Desktop (Remote MCP Server)

**Config location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration for HTTP transport:**

```json
{
  "mcpServers": {
    "pythontrio": {
      "url": "http://localhost:8000/mcp/",
      "transport": "streamable-http"
    }
  }
}
```

**For remote deployment:**

```json
{
  "mcpServers": {
    "pythontrio": {
      "url": "https://your-server.com/mcp/",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### Cursor IDE

Cursor uses the same MCP configuration format. Add to Cursor settings:

```json
{
  "mcp.servers": {
    "pythontrio": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

### Claude Code CLI

```bash
# Add to .claude/settings.json in your project
{
  "mcpServers": {
    "pythontrio": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

### Any MCP-Compatible Client (Python)

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(tools)

            # Call a tool
            result = await session.call_tool("list_assets", {})
            print(result)
```

---

## 6. Authentication (Production)

For production deployment, add API key authentication:

**File to create:** `app/mcp_auth.py`

```python
"""MCP authentication middleware."""

import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

MCP_API_KEY = os.getenv("MCP_API_KEY")


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Validate API key for MCP endpoints."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            if MCP_API_KEY:
                auth_header = request.headers.get("Authorization")
                if not auth_header or auth_header != f"Bearer {MCP_API_KEY}":
                    raise HTTPException(status_code=401, detail="Invalid API key")
        return await call_next(request)
```

**Add to main.py:**

```python
from app.mcp_auth import MCPAuthMiddleware

app.add_middleware(MCPAuthMiddleware)
```

Set the API key via environment:

```bash
export MCP_API_KEY="your-secret-key"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 7. Testing

### Manual Testing with MCP Inspector

```bash
# Test HTTP endpoint
npx @anthropic/mcp-inspector http://localhost:8000/mcp
```

### Unit Tests for ReadService

**File to create:** `tests/test_read_service.py`

```python
"""Tests for ReadService."""

import pytest
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user_profile import UserProfile
from app.services.read_service import ReadService


def test_list_assets_returns_ordered_by_symbol(db_session: Session):
    """Assets should be returned ordered by symbol."""
    db_session.add(Asset(symbol="ZZZ", name="Last", asset_type="crypto"))
    db_session.add(Asset(symbol="AAA", name="First", asset_type="crypto"))
    db_session.commit()

    service = ReadService(db_session)
    assets = service.list_assets()

    symbols = [a.symbol for a in assets]
    assert symbols.index("AAA") < symbols.index("ZZZ")


def test_list_users_filters_inactive_by_default(db_session: Session):
    """Only active users should be returned by default."""
    db_session.add(UserProfile(email="active@test.com", is_active=True))
    db_session.add(UserProfile(email="inactive@test.com", is_active=False))
    db_session.commit()

    service = ReadService(db_session)
    users = service.list_users(active_only=True)

    emails = [u.email for u in users]
    assert "active@test.com" in emails
    assert "inactive@test.com" not in emails
```

### Integration Test for MCP Endpoint

**File to create:** `tests/integration/test_mcp_endpoint.py`

```python
"""Integration tests for MCP HTTP endpoint."""

from fastapi.testclient import TestClient


def test_mcp_endpoint_accessible(client: TestClient):
    """MCP endpoint should respond to POST requests."""
    # MCP uses POST for tool calls
    response = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    })
    # Should not return 404
    assert response.status_code != 404
```

Run tests:

```bash
pytest tests/test_read_service.py tests/integration/test_mcp_endpoint.py -v
```

---

## 8. Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Client (Claude, Cursor, custom agent)                          │
│  ─────────────────────────────────────────                          │
│  POST http://localhost:8000/mcp                                     │
│  {"jsonrpc": "2.0", "method": "tools/call",                        │
│   "params": {"name": "list_assets"}}                                │
│                    │                                                 │
│                    ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI + FastMCP (Streamable HTTP)                        │   │
│  │  ───────────────────────────────────                        │   │
│  │  1. Receives JSON-RPC request at /mcp                       │   │
│  │  2. Routes to list_assets() tool                            │   │
│  │  3. Creates SessionLocal() for this request                 │   │
│  │  4. Instantiates ReadService(db)                            │   │
│  │  5. Calls service.list_assets()                             │   │
│  │  6. Converts ORM models to dicts                            │   │
│  │  7. Returns JSON-RPC response                               │   │
│  │  8. Closes session in finally block                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                    │                                                 │
│                    ▼                                                 │
│  JSON-RPC response with asset list                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Project Structure After Implementation

```
python_trio/
├── app/
│   ├── main.py               # MODIFIED: Mount MCP at /mcp
│   ├── mcp_server.py         # NEW: FastMCP server with tools
│   ├── mcp_auth.py           # NEW: Optional auth middleware
│   ├── schemas/
│   │   ├── __init__.py       # MODIFIED: Export shared schemas
│   │   ├── onboarding.py     # (existing)
│   │   └── responses.py      # NEW: Shared response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── onboarding_service.py
│   │   └── read_service.py   # NEW: Read-only query service
│   └── ...
├── tests/
│   ├── test_read_service.py  # NEW: ReadService unit tests
│   └── integration/
│       └── test_mcp_endpoint.py  # NEW: MCP endpoint tests
├── requirements.txt          # MODIFIED: Added fastmcp>=2.0.0
└── Makefile                  # MODIFIED: Added serve, mcp-local targets
```

---

## 10. Deployment Checklist

- [ ] Add `fastmcp>=2.0.0` to requirements.txt
- [ ] Create `app/schemas/responses.py` (shared Pydantic schemas)
- [ ] Update `app/schemas/__init__.py` (export new schemas)
- [ ] Refactor `app/routers/assets.py` (use shared AssetResponse)
- [ ] Refactor `app/routers/portfolios.py` (use shared PortfolioResponse)
- [ ] Refactor `app/routers/user_profiles.py` (use shared UserProfileResponse)
- [ ] Refactor `app/routers/holdings.py` (use shared HoldingResponse)
- [ ] Create `app/services/read_service.py`
- [ ] Create `app/mcp_server.py`
- [ ] Mount MCP in `app/main.py`
- [ ] Update Makefile with `serve` and `mcp-local` targets
- [ ] Add tests
- [ ] Run existing tests to verify router refactor didn't break anything
- [ ] Set `MCP_API_KEY` environment variable (production)
- [ ] Configure Claude Desktop / Cursor with server URL
- [ ] Test with MCP Inspector

---

## 11. Future Enhancements

**A. Write tools** - Add `create_asset`, `add_holding` using OnboardingService pattern with proper auth checks.

**B. Resources** - Expose `portfolio://{id}` as MCP resources for direct context loading.

**C. Prompts** - Add reusable prompt templates like `analyze_portfolio`.

**D. WebSocket transport** - For real-time streaming of price updates.

**E. OAuth 2.1** - Replace API key with OAuth for multi-tenant deployments.