from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import UserCreateAdmin, UserUpdateAdmin, LicenseUpdate
import json
import secrets
from erin.api.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/users", response_model=List[Dict[str, Any]])
async def get_users(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    if "ADMIN" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT id, username, email, roles, mfa_enabled, last_login, created_at FROM users LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [dict(row) for row in cursor.fetchall()]

@router.post("/users", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreateAdmin, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    if "ADMIN" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user.username, user.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        from erin.api.routers.auth import get_password_hash
        hashed = get_password_hash(secrets.token_urlsafe(16))
        user_id = secrets.token_urlsafe(16)
        roles = json.dumps(user.roles)
        now = datetime.utcnow()
        
        conn.execute(
            """INSERT INTO users (id, username, email, password_hash, roles, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, user.username, user.email, hashed, roles, now, now)
        )
        
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(cursor.fetchone())

@router.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_user(user_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    if "ADMIN" not in current_user["roles"] and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)

@router.put("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(
    user_id: str,
    update: UserUpdateAdmin,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    if "ADMIN" not in current_user["roles"] and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        updates = []
        params = []
        if update.roles is not None:
            updates.append("roles = ?")
            params.append(json.dumps(update.roles))
        if update.locked is not None:
            updates.append("locked_until = ?")
            params.append(datetime.utcnow() if update.locked else None)
        
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.utcnow())
            params.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(cursor.fetchone())

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    if "ADMIN" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

# Audit
@router.get("/audit", response_model=Dict[str, Any])
async def get_audit_log(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    limit: int = Query(100, le=1000),
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    if "ADMIN" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if action:
            query += " AND action = ?"
            params.append(action)
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        return {"items": [dict(row) for row in cursor.fetchall()], "total": len(params)}

# Data Licenses
@router.get("/licenses", response_model=List[Dict[str, Any]])
async def get_licenses(current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    if "ADMIN" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM data_licenses")
        return [dict(row) for row in cursor.fetchall()]

@router.put("/licenses/{provider}/{dataset}", response_model=Dict[str, Any])
async def update_license(
    provider: str,
    dataset: str,
    license: LicenseUpdate,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    if "ADMIN" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM data_licenses WHERE provider = ? AND dataset = ?",
            (provider, dataset)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="License not found")
        
        conn.execute(
            """UPDATE data_licenses SET commercial_use = ?, redistribution = ?, caching_allowed = ?,
               caching_max_age_days = ?, attribution_required = ?, attribution_text = ?,
               retention_max_days = ?, status = ?, last_reviewed = ?, reviewed_by = ?
               WHERE provider = ? AND dataset = ?""",
            (license.commercial_use, license.redistribution, license.caching_allowed,
             license.caching_max_age_days, license.attribution_required, license.attribution_text,
             license.retention_max_days, license.status, date.today(), current_user["id"],
             provider, dataset)
        )
        
        cursor = conn.execute(
            "SELECT * FROM data_licenses WHERE provider = ? AND dataset = ?",
            (provider, dataset)
        )
        return dict(cursor.fetchone())