"""FastAPI application entry point."""

from fastapi import FastAPI

from app.config import settings
from app.routers import assets_router, portfolios_router

app = FastAPI(title=settings.app_name)

app.include_router(assets_router)
app.include_router(portfolios_router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning a welcome message."""
    return {"message": f"Welcome to {settings.app_name}"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
