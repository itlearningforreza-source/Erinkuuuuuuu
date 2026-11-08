from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction, get_duckdb_db
from erin.api.models import BondBase, BondAnalytics

router = APIRouter(prefix="/api/v1/fixed-income", tags=["fixed-income"])

@router.get("/bonds", response_model=Dict[str, Any])
async def get_bonds(
    issuer: Optional[str] = Query(None),
    rating: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM bonds WHERE 1=1"
        params = []
        
        if issuer:
            query += " AND issuer LIKE ?"
            params.append(f"%{issuer}%")
        if rating:
            query += " AND credit_rating = ?"
            params.append(rating)
        
        query += " ORDER BY issuer LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        bonds = [dict(row) for row in cursor.fetchall()]
        
        return {"items": bonds, "total": len(bonds), "page": 1, "page_size": limit}

@router.get("/bonds/{figi}")
async def get_bond(figi: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM bonds WHERE figi = ?", (figi,))
        bond = cursor.fetchone()
        if not bond:
            raise HTTPException(status_code=404, detail="Bond not found")
        return dict(bond)

@router.get("/bonds/{figi}/analytics", response_model=BondAnalytics)
async def get_bond_analytics(
    figi: str,
    settlement: date = Query(...),
    yield_: Optional[Decimal] = Query(None, alias="yield"),
    db = Depends(get_duckdb_db)
):
    # In a real implementation, this would calculate bond analytics
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/curves", response_model=Dict[str, Any])
async def get_yield_curves(
    currency: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    date: Optional[date] = Query(None),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM yield_curves WHERE 1=1"
        params = []
        
        if currency:
            query += " AND currency = ?"
            params.append(currency)
        if type:
            query += " AND curve_type = ?"
            params.append(type)
        if date:
            query += " AND reference_date = ?"
            params.append(date)
        
        query += " ORDER BY reference_date DESC LIMIT 50"
        
        cursor = conn.execute(query, params)
        curves = [dict(row) for row in cursor.fetchall()]
        
        return {"items": curves, "total": len(curves)}

@router.get("/curves/{curve_id}")
async def get_yield_curve(curve_id: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM yield_curves WHERE id = ?", (curve_id,))
        curve = cursor.fetchone()
        if not curve:
            raise HTTPException(status_code=404, detail="Yield curve not found")
        return dict(curve)

@router.get("/curves/{curve_id}/interpolate")
async def interpolate_curve(
    curve_id: str,
    tenors: str = Query(..., description="Comma-separated tenors (e.g., 1M,3M,6M,1Y,2Y,5Y,10Y,30Y)"),
    db = Depends(get_sqlite_db)
):
    raise HTTPException(status_code=501, detail="Not implemented")