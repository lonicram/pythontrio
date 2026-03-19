"""Tests for Portfolio schemas."""

import pytest

from app.schemas import PortfolioCreate, PortfolioResponse

# ============================================================================
# Portfolio Schema Validation Tests
# ============================================================================


@pytest.mark.parametrize(
    "name",
    [
        "My Portfolio",
        "Retirement Fund",
        "Short-term Trading",
        "Cryptocurrency Holdings",
    ],
    ids=["simple", "retirement", "trading", "crypto"],
)
def test_portfolio_create_valid_names(name: str) -> None:
    """Test creating portfolios with various names.

    Args:
        name: Portfolio name.
    """
    portfolio = PortfolioCreate(name=name)

    assert portfolio.name == name


def test_portfolio_create_optional_description() -> None:
    """Test that description is optional in PortfolioCreate."""
    portfolio_without_desc = PortfolioCreate(name="Test Portfolio")
    assert portfolio_without_desc.description is None

    portfolio_with_desc = PortfolioCreate(
        name="Test Portfolio",
        description="A test portfolio for unit testing",
    )
    assert portfolio_with_desc.description == "A test portfolio for unit testing"


def test_portfolio_response_includes_id() -> None:
    """Test that PortfolioResponse includes required database fields."""
    portfolio = PortfolioResponse(
        id=1,
        name="My Portfolio",
    )

    assert portfolio.id == 1
    assert portfolio.name == "My Portfolio"


def test_portfolio_response_with_description() -> None:
    """Test PortfolioResponse with description."""
    portfolio = PortfolioResponse(
        id=1,
        name="My Portfolio",
        description="My test portfolio",
    )

    assert portfolio.id == 1
    assert portfolio.name == "My Portfolio"
    assert portfolio.description == "My test portfolio"
