"""Asset routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import Asset, Portfolio

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
)


@router.get("/", response_model=list[schemas.AssetResponse])
def list_assets(db: Session = Depends(get_db)) -> list[Asset]:
    """Retrieve all assets."""
    return db.query(Asset).all()


@router.get("/{asset_id}", response_model=schemas.AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)) -> Asset:
    """Retrieve a single asset by ID.

    Args:
        asset_id: The ID of the asset to retrieve.
        db: Database session.

    Returns:
        The asset with the specified ID.

    Raises:
        HTTPException: 404 if asset not found.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=404, detail=f"Asset with id {asset_id} not found"
        )
    return asset


@router.post("/", response_model=schemas.AssetResponse, status_code=201)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)) -> Asset:
    """Create a new asset.

    Args:
        asset: Asset creation data.
        db: Database session.

    Returns:
        The created asset.

    Raises:
        HTTPException: 400 if portfolio does not exist.
    """
    # Validate that the portfolio exists
    portfolio = db.query(Portfolio).filter(Portfolio.id == asset.portfolio_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=400,
            detail=f"Portfolio with id {asset.portfolio_id} does not exist",
        )

    db_asset = Asset(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset
