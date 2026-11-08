from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import OptionBase, OptionPrice, OptionGreeks

router = APIRouter(prefix="/api/v1/derivatives", tags=["derivatives"])

@router.get("/options", response_model=Dict[str, Any])
async def get_options(
    underlying: Optional[str] = Query(None),
    expiration: Optional[date] = Query(None),
    limit: int = Query(50, le=200),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM options WHERE 1=1"
        params = []
        
        if underlying:
            query += " AND underlying_figi = ?"
            params.append(underlying)
        if expiration:
            query += " AND expiration = ?"
            params.append(expiration)
        
        query += " ORDER BY expiration LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        options = [dict(row) for row in cursor.fetchall()]
        
        return {"items": options, "total": len(options), "page": 1, "page_size": limit}

@router.get("/options/{figi}")
async def get_option(figi: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM options WHERE figi = ?", (figi,))
        option = cursor.fetchone()
        if not option:
            raise HTTPException(status_code=404, detail="Option not found")
        return dict(option)

@router.get("/options/{figi}/price", response_model=OptionPrice)
async def price_option(
    figi: str,
    model: str = Query(..., description="BSM|BINOMIAL"),
    spot: Decimal = Query(...),
    rate: Decimal = Query(...),
    vol: Decimal = Query(...),
    dividend_yield: Optional[Decimal] = Query(None),
    db = Depends(get_sqlite_db)
):
    # In a real implementation, this would call the pricing engine
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/vol-surfaces", response_model=Dict[str, Any])
async def get_vol_surfaces(
    underlying: Optional[str] = Query(None),
    date: Optional[date] = Query(None),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM volatility_surfaces WHERE 1=1"
        params = []
        
        if underlying:
            query += " AND underlying_figi = ?"
            params.append(underlying)
        if date:
            query += " AND reference_date = ?"
            params.append(date)
        
        query += " ORDER BY reference_date DESC LIMIT 20"
        
        cursor = conn.execute(query, params)
        surfaces = [dict(row) for row in cursor.fetchall()]
        
        return {"items": surfaces, "total": len(surfaces)}

@router.get("/vol-surfaces/{surface_id}")
async def get_vol_surface(surface_id: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM volatility_surfaces WHERE id = ?", (surface_id,))
        surface = cursor.fetchone()
        if not surface:
            raise HTTPException(status_code=404, detail="Volatility surface not found")
        return dict(surface)

@router.get("/vol-surfaces/{surface_id}/interpolate")
async def interpolate_vol_surface(
    surface_id: str,
    expiry: date = Query(...),
    strike: Decimal = Query(...),
    db = Depends(get_sqlite_db)
):
    raise HTTPException(status_code=501, detail="Not implemented")