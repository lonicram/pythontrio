"""Asset routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.models import Asset

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
    """Retrieve a single asset by ID."""
    asset = db.query(Asset).filter(Asset.id == asset_id).one()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/", response_model=schemas.AssetResponse, status_code=201)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)) -> Asset:
    """Create a new asset."""
    db_asset = Asset(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset
