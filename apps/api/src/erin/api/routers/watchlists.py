from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction

router = APIRouter(prefix="/api/v1/watchlists", tags=["watchlists"])

class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    symbols: List[str] = Field(default_factory=list)

class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbols: Optional[List[str]] = None

class WatchlistResponse(BaseModel):
    id: str
    user_id: str
    name: str
    symbols: List[str]
    created_at: datetime
    updated_at: datetime

@router.get("", response_model=List[WatchlistResponse])
async def get_watchlists(current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM watchlists WHERE user_id = ? ORDER BY created_at DESC",
            (current_user["id"],)
        )
        watchlists = [dict(row) for row in cursor.fetchall()]
        return [WatchlistResponse(**wl) for wl in watchlists]

@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(watchlist: WatchlistCreate, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        watchlist_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        conn.execute(
            """INSERT INTO watchlists (id, user_id, name, symbols, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (watchlist_id, current_user["id"], watchlist.name, 
             json.dumps(watchlist.symbols), now, now)
        )
        
        cursor = conn.execute("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))
        return WatchlistResponse(**dict(cursor.fetchone()))

@router.get("/{watchlist_id}", response_model=WatchlistResponse)
async def get_watchlist(watchlist_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, current_user["id"])
        )
        watchlist = cursor.fetchone()
        if not watchlist:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        return WatchlistResponse(**dict(watchlist))

@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: str, 
    update: WatchlistUpdate, 
    current_user = Depends(get_current_user), 
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, current_user["id"])
        )
        watchlist = cursor.fetchone()
        if not watchlist:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        updates = []
        params = []
        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if update.symbols is not None:
            updates.append("symbols = ?")
            params.append(json.dumps(update.symbols))
        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(watchlist_id)
        
        conn.execute(f"UPDATE watchlists SET {', '.join(updates)} WHERE id = ?", params)
        
        cursor = conn.execute("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))
        return WatchlistResponse(**dict(cursor.fetchone()))

@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(watchlist_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "DELETE FROM watchlists WHERE id = ? AND user_id = ?",
            (watchlist_id, current_user["id"])
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Watchlist not found")

from typing import Optional
from fastapi import WebSocket
from erin.api.core.database import get_sqlite_db, sqlite_transaction
import json
import secrets