from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import (
    CompanyResponse, CompanyCreate, FinancialStatementBase, FinancialStatementResponse,
    FinancialRatio, ValuationModelResponse, ValuationModelType, ValuationRunRequest, ValuationRunResponse
)

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])

@router.get("", response_model=Dict[str, Any])
async def search_companies(
    search: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM companies WHERE is_active = 1"
        params = []
        
        if search:
            query += " AND (name LIKE ? OR cik LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if sector:
            query += " AND sector = ?"
            params.append(sector)
        
        query += " ORDER BY name LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        companies = [CompanyResponse(**dict(row)) for row in cursor.fetchall()]
        
        count_query = "SELECT COUNT(*) FROM companies WHERE is_active = 1"
        count_params = []
        if search:
            count_query += " AND (name LIKE ? OR cik LIKE ?)"
            count_params.extend([f"%{search}%", f"%{search}%"])
        if sector:
            count_query += " AND sector = ?"
            count_params.append(sector)
        
        cursor = conn.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        return {"items": companies, "total": total, "page": 1, "page_size": limit}

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        company = cursor.fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        return CompanyResponse(**dict(company))

@router.get("/{company_id}/financials", response_model=Dict[str, Any])
async def get_company_financials(
    company_id: str,
    statement_type: Optional[str] = Query(None, description="income|balance_sheet|cash_flow"),
    period_type: Optional[str] = Query(None, description="quarterly|annual"),
    limit: int = Query(20, le=100),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM financial_statements WHERE company_id = ?"
        params = [company_id]
        
        if statement_type:
            query += " AND statement_type = ?"
            params.append(statement_type.upper())
        if period_type:
            query += " AND period_type = ?"
            params.append(period_type.upper())
        
        query += " ORDER BY period_end DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        financials = [dict(row) for row in cursor.fetchall()]
        
        return {"items": financials, "company_id": company_id}

@router.get("/{company_id}/ratios", response_model=Dict[str, Any])
async def get_company_ratios(
    company_id: str,
    period_end: Optional[date] = Query(None),
    ratio_type: Optional[str] = Query(None, description="profitability|liquidity|solvency|efficiency|valuation"),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM financial_ratios WHERE company_id = ?"
        params = [company_id]
        
        if period_end:
            query += " AND period_end = ?"
            params.append(period_end)
        if ratio_type:
            query += " AND ratio_type = ?"
            params.append(ratio_type.upper())
        
        query += " ORDER BY period_end DESC"
        
        cursor = conn.execute(query, params)
        ratios = [dict(row) for row in cursor.fetchall()]
        
        return {"ratios": ratios}

@router.get("/{company_id}/peers", response_model=Dict[str, Any])
async def get_company_peers(
    company_id: str,
    method: str = Query("gics", description="gics|custom"),
    limit: int = Query(10, le=50),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        company = cursor.fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if method == "gics" and company["gics_code"]:
            cursor = conn.execute(
                "SELECT * FROM companies WHERE gics_code = ? AND id != ? LIMIT ?",
                (company["gics_code"], company_id, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM companies WHERE sector = ? AND id != ? LIMIT ?",
                (company["sector"], company_id, limit)
            )
        
        peers = [CompanyResponse(**dict(row)) for row in cursor.fetchall()]
        return {"peers": peers}