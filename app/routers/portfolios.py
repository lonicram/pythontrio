"""Portfolio routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio
from app import schemas

router = APIRouter(
    prefix="/portfolios",
    tags=["portfolios"],
)


@router.get("/", response_model=list[schemas.PortfolioResponse])
def list_portfolios(db: Session = Depends(get_db)) -> list[Portfolio]:
    """Retrieve all portfolios."""
    return db.query(Portfolio).all()


@router.get("/{portfolio_id}", response_model=schemas.PortfolioResponse)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> Portfolio:
    """Retrieve a single portfolio by ID."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).one()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.post("/", response_model=schemas.PortfolioResponse, status_code=201)
def create_portfolio(
    portfolio: schemas.PortfolioCreate, db: Session = Depends(get_db)
) -> Portfolio:
    """Create a new portfolio."""
    db_portfolio = Portfolio(**portfolio.model_dump())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a portfolio by ID."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()