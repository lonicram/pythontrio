"""FastAPI application entry point."""

import logging
import os
import uuid
from contextvars import ContextVar

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.mcp_server import mcp
from app.routers import (
    asset_prices,
    assets,
    holdings,
    onboarding,
    portfolios,
    user_profiles,
)

# --- Logging setup ---

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(request_id)s] %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
for _h in logging.root.handlers:
    _h.addFilter(_RequestIDFilter())


class _RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = _request_id_var.set(str(uuid.uuid4())[:8])
        try:
            return await call_next(request)
        finally:
            _request_id_var.reset(token)


# --- App setup ---

# Create MCP HTTP app first to get its lifespan
mcp_app = mcp.http_app(path="/")

# Pass MCP lifespan to FastAPI (required for MCP session management)
app = FastAPI(title=settings.app_name, lifespan=mcp_app.lifespan)
app.add_middleware(_RequestIDMiddleware)

# REST API routers
app.include_router(user_profiles.router)
app.include_router(portfolios.router)
app.include_router(assets.router)
app.include_router(holdings.router)
app.include_router(asset_prices.router)
app.include_router(onboarding.router)

# Static files (admin UI assets)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# MCP endpoint (Streamable HTTP)
app.mount("/mcp", mcp_app)


@app.get("/admin", response_class=FileResponse, include_in_schema=False)
def admin_ui() -> FileResponse:
    """Serve the admin console UI."""
    return FileResponse(os.path.join(_static_dir, "admin.html"), media_type="text/html")


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning a welcome message."""
    return {"message": f"Welcome to {settings.app_name}"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
