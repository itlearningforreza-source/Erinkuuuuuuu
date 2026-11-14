"""Portfolios Router."""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


router = APIRouter(tags=["Portfolios"])


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_currency: str = "USD"
    description: str = ""


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PositionCreate(BaseModel):
    symbol: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    avg_cost: float = Field(..., gt=0)
    currency: str = "USD"


class PortfolioResponse(BaseModel):
    id: str
    name: str
    base_currency: str
    total_value: float
    cash: float
    positions: dict
    created_at: datetime
    updated_at: datetime


@router.post("/", response_model=dict)
async def create_portfolio(portfolio: dict):
    """Create a new portfolio."""
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "name": "My Portfolio",
        "base_currency": "USD",
        "total_value": 100000.0,
        "cash": 50000.0,
        "positions": {},
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
    }


@router.get("/", response_model=List[dict])
async def get_portfolios():
    """Get all portfolios."""
    return [
        {
            "id": "port_1",
            "name": "Main Portfolio",
            "base_currency": "USD",
            "total_value": 150000.0,
            "cash": 25000.0,
            "positions": {
                "AAPL": {"quantity": 100, "avg_cost": 150.0, "current_price": 150.25, "market_value": 15025.0, "unrealized_pnl": 25.0, "unrealized_pnl_pct": 0.17},
                "MSFT": {"quantity": 50, "avg_cost": 300.0, "current_price": 350.0, "market_value": 17500.0, "unrealized_pnl": 2500.0, "unrealized_pnl_pct": 16.67},
            },
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }
    ]


@router.get("/{portfolio_id}")
async def get_portfolio(portfolio_id: str):
    """Get portfolio details."""
    return {
        "id": "port_1",
        "name": "Main Portfolio",
        "base_currency": "USD",
        "total_value": 150000.0,
        "cash": 25000.0,
        "positions": {
            "AAPL": {"quantity": 100, "avg_cost": 150.0, "current_price": 150.25, "market_value": 15025.0, "unrealized_pnl": 25.0, "unrealized_pnl_pct": 0.17},
            "MSFT": {"quantity": 50, "avg_cost": 300.0, "current_price": 350.0, "market_value": 17500.0, "unrealized_pnl": 2500.0, "unrealized_pnl_pct": 16.67},
        },
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
    }


@router.put("/{portfolio_id}")
async def update_portfolio(portfolio_id: str, portfolio: dict):
    """Update portfolio."""
    return {"message": "Portfolio updated"}


@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    """Delete a portfolio."""
    return {"message": "Portfolio deleted"}


@router.post("/{portfolio_id}/positions")
async def add_position(portfolio_id: str, position: dict):
    """Add position to portfolio."""
    return {
        "figi": "FIGI_AAPL",
        "symbol": "AAPL",
        "quantity": 10,
        "avg_cost": 150.0,
        "currency": "USD",
    }


@router.put("/{portfolio_id}/positions/{symbol}")
async def update_position(portfolio_id: str, symbol: str, position: dict):
    """Update position."""
    return {"message": "Position updated"}


@router.delete("/{portfolio_id}/positions/{symbol}")
async def remove_position(portfolio_id: str, symbol: str):
    """Remove position from portfolio."""
    return {"message": "Position removed"}


@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(portfolio_id: str, period: str = "1Y"):
    """Get portfolio performance metrics."""
    return {
        "portfolio_id": "port_1",
        "period": period,
        "total_return": 0.15,
        "annualized_return": 0.12,
        "volatility": 0.18,
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.12,
        "beta": 1.1,
        "tracking_error": 0.05,
        "information_ratio": 0.5,
        "attribution": {
            "allocation": 0.02,
            "selection": 0.01,
            "interaction": 0.00,
        },
    }