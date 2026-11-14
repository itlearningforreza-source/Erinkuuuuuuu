from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import (
    VaRModelResponse, VaRMethod, VaRResult, VaRModelBase
)
import secrets
from erin.api.routers.auth import get_current_user
from fastapi import Body

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

@router.get("/var/models", response_model=List[VaRModelResponse])
async def get_var_models(db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM var_models WHERE is_active = 1")
        return [VaRModelResponse(**dict(row)) for row in cursor.fetchall()]

@router.post("/var/models", response_model=VaRModelResponse, status_code=status.HTTP_201_CREATED)
async def create_var_model(model: VaRModelBase, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        model_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        conn.execute(
            """INSERT INTO var_models (id, name, method, confidence_level, horizon_days, lookback_days, 
               distribution_assumption, n_simulations, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (model_id, model.name, model.method.value, model.confidence_level, model.horizon_days,
             model.lookback_days, model.distribution_assumption, model.n_simulations,
             current_user["id"], datetime.utcnow())
        )
        
        cursor = conn.execute("SELECT * FROM var_models WHERE id = ?", (model_id,))
        return VaRModelResponse(**dict(cursor.fetchone()))

@router.get("/var/models/{model_id}", response_model=VaRModelResponse)
async def get_var_model(model_id: str, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM var_models WHERE id = ?", (model_id,))
        model = cursor.fetchone()
        if not model:
            raise HTTPException(status_code=404, detail="VaR model not found")
        return VaRModelResponse(**dict(model))

@router.post("/var/calculate", response_model=Dict[str, str], status_code=status.HTTP_202_ACCEPTED)
async def calculate_var(
    model_id: str = Body(...),
    portfolio_id: str = Body(...),
    as_of_date: date = Body(...),
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    result_id = secrets.token_urlsafe(16)
    # In a real implementation, this would queue a background job
    return {"result_id": result_id, "status": "PENDING"}

@router.get("/var/results/{result_id}", response_model=VaRResult)
async def get_var_result(result_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM var_results WHERE id = ?", (result_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="VaR result not found")
        return VaRResult(**dict(result))

@router.get("/var/results", response_model=Dict[str, Any])
async def get_var_results(
    portfolio_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        query = "SELECT * FROM var_results WHERE 1=1"
        params = []
        
        if portfolio_id:
            query += " AND portfolio_id = ?"
            params.append(portfolio_id)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return {"items": results, "total": len(results), "page": 1, "page_size": limit}

# Stress Tests
class StressTestCreate(BaseModel):
    name: str
    scenario_type: str  # HISTORICAL, HYPOTHETICAL, REGULATORY
    shocks: Dict[str, Dict[str, Any]]
    portfolio_id: str

class StressTestResponse(BaseModel):
    id: str
    name: str
    scenario_type: str
    shocks: Dict[str, Dict[str, Any]]
    portfolio_id: str
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True

@router.post("/stress-tests", response_model=StressTestResponse, status_code=status.HTTP_201_CREATED)
async def create_stress_test(test: StressTestCreate, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/stress-tests/{test_id}", response_model=StressTestResponse)
async def get_stress_test(test_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    raise HTTPException(status_code=404, detail="Not implemented")

