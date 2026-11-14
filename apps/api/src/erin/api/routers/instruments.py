from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import (
    AssetClass, InstrumentBase, InstrumentCreate, InstrumentResponse, InstrumentSearch
)

router = APIRouter(prefix="/api/v1/instruments", tags=["instruments"])


@router.get("", response_model=Dict[str, Any])
async def search_instruments(
    search: Optional[str] = Query(None),
    asset_class: Optional[AssetClass] = Query(None),
    exchange: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db = Depends(get_sqlite_db)
):
    """Search instruments."""
    with sqlite_transaction() as conn:
        query = "SELECT * FROM instruments WHERE is_active = 1"
        params = []
        
        if search:
            query += " AND (composite_ticker LIKE ? OR name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if asset_class:
            query += " AND asset_class = ?"
            params.append(asset_class.value)
        if exchange:
            query += " AND primary_exchange = ?"
            params.append(exchange)
        
        query += " ORDER BY composite_ticker LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        instruments = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM instruments WHERE is_active = 1"
        count_params = []
        if search:
            count_query += " AND (composite_ticker LIKE ? OR name LIKE ?)"
            count_params.extend([f"%{search}%", f"%{search}%"])
        if asset_class:
            count_query += " AND asset_class = ?"
            count_params.append(asset_class.value)
        if exchange:
            count_query += " AND primary_exchange = ?"
            count_params.append(exchange)
        
        cursor = conn.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        return {
            "items": [InstrumentResponse(**inst) for inst in instruments],
            "total": total,
            "page": 1,
            "page_size": limit
        }

@router.get("/{figi}", response_model=InstrumentResponse)
async def get_instrument(figi: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM instruments WHERE figi = ?", (figi,))
        instrument = cursor.fetchone()
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument not found")
        return InstrumentResponse(**dict(instrument))

@router.get("/{figi}/aliases")
async def get_instrument_aliases(figi: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM instrument_aliases WHERE figi = ? ORDER BY valid_from DESC",
            (figi,)
        )
        aliases = [dict(row) for row in cursor.fetchall()]
        return {"aliases": aliases}