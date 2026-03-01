"""FastAPI application entry point."""

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.database import get_db

app = FastAPI(title=settings.app_name)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning a welcome message."""
    return {"message": f"Welcome to {settings.app_name}"}


@app.get("/assets", response_model=list[schemas.ItemResponse])
def read_assets() -> list[schemas.ItemResponse]:
    """Retrieve all assets."""



@app.get("/assets/{asset_id}", response_model=schemas.ItemResponse)
def read_asset() -> schemas.ItemResponse:
    """Retrieve a single assets by ID."""


@app.post("/assets", response_model=schemas.ItemResponse, status_code=201)
def create_asset() -> schemas.ItemResponse:
    """Create a new asset."""
