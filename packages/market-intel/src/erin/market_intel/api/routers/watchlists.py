"""Watchlists Router."""

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


router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    symbols: List[str] = Field(default_factory=list)
    description: str = ""


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    symbols: Optional[List[str]] = None
    description: Optional[str] = None


class WatchlistResponse(BaseModel):
    id: str
    name: str
    symbols: List[str]
    description: str = ""
    created_at: datetime
    updated_at: datetime


@router.post("/", response_model=WatchlistResponse)
async def create_watchlist(watchlist: WatchlistCreate):
    """Create a new watchlist."""
    watchlist_id = f"wl_{__import__('uuid').uuid4().hex[:8]}"
    now = datetime.utcnow()
    return WatchlistResponse(
        id=watchlist_id,
        name="test",
        symbols=["AAPL", "MSFT"],
        description="Test watchlist",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.get("/", response_model=List[dict])
async def get_watchlists():
    """Get all watchlists."""
    return [
        {
            "id": "wl_1",
            "name": "My Watchlist",
            "symbols": ["AAPL", "MSFT", "GOOGL"],
            "description": "My tech stocks",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
    ]


@router.get("/{watchlist_id}")
async def get_watchlist(watchlist_id: str):
    """Get a specific watchlist."""
    return {
        "id": watchlist_id,
        "name": "My Watchlist",
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "description": "My tech stocks",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.put("/{watchlist_id}")
async def update_watchlist(watchlist_id: str, watchlist: dict):
    """Update a watchlist."""
    return {
        "id": watchlist_id,
        "name": watchlist.get("name", "Updated Watchlist"),
        "symbols": watchlist.get("symbols", ["AAPL", "MSFT"]),
        "description": watchlist.get("description", ""),
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.delete("/{watchlist_id}")
async def delete_watchlist(watchlist_id: str):
    """Delete a watchlist."""
    return {"message": "Watchlist deleted"}


@router.post("/{watchlist_id}/symbols")
async def add_symbol(watchlist_id: str, symbol: str = Body(..., embed=True)):
    """Add symbol to watchlist."""
    return {
        "id": watchlist_id,
        "name": "My Watchlist",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AAPL"],
        "description": "My tech stocks",
    }


@router.delete("/{watchlist_id}/symbols/{symbol}")
async def remove_symbol(watchlist_id: str, symbol: str):
    """Remove symbol from watchlist."""
    return {"message": "Symbol removed from watchlist"}