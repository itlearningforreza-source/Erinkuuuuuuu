from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import (
    RAGQuery, RAGResult, RAGQueryResponse, ToolCallRequest, ToolCallResponse,
    ToolCallStatus
)
import json
import secrets
from erin.api.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

@router.post("/rag/query", response_model=RAGQueryResponse)
async def query_rag(query: RAGQuery, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    # In a real implementation, this would query the vector database
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/tools", response_model=List[Dict[str, Any]])
async def get_tools(current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT name, version, description, input_schema, output_schema, read_only, sensitivity, allowed_roles, rate_limit, timeout_seconds, sandbox_profile FROM tool_definitions WHERE is_active = 1"
        )
        tools = []
        for row in cursor.fetchall():
            tool = dict(row)
            tool["input_schema"] = json.loads(tool["input_schema"])
            tool["output_schema"] = json.loads(tool["output_schema"])
            tool["allowed_roles"] = json.loads(tool["allowed_roles"])
            tool["rate_limit"] = json.loads(tool["rate_limit"]) if tool["rate_limit"] else None
            tools.append(tool)
        return tools

@router.post("/tools/execute", response_model=ToolCallResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_tool(call: ToolCallRequest, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    # In a real implementation, this would execute the tool in a sandbox
    call_id = secrets.token_urlsafe(16)
    return ToolCallResponse(call_id=call_id, status="PENDING")

@router.get("/tools/calls/{call_id}", response_model=ToolCallStatus)
async def get_tool_call(call_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM tool_calls WHERE id = ? AND user_id = ?",
            (call_id, current_user["id"])
        )
        call = cursor.fetchone()
        if not call:
            raise HTTPException(status_code=404, detail="Tool call not found")
        return ToolCallStatus(**dict(call))

@router.post("/reports/generate", response_model=Dict[str, str], status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    template: str = Body(...),
    evidence: List[Dict[str, Any]] = Body(...),
    format: str = Body("markdown"),
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    report_id = secrets.token_urlsafe(16)
    return {"report_id": report_id}