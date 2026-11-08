from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import (
    PortfolioResponse, PortfolioCreate, PositionResponse, PositionBase,
    TransactionBase, TransactionResponse, VaRModelResponse, VaRMethod, VaRResult
)

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])

@router.get("", response_model=List[PortfolioResponse])
async def get_portfolios(current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM portfolios WHERE user_id = ? ORDER BY created_at DESC",
            (current_user["id"],)
        )
        return [PortfolioResponse(**dict(row)) for row in cursor.fetchall()]

@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(portfolio: PortfolioCreate, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        portfolio_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        conn.execute(
            """INSERT INTO portfolios (id, user_id, name, base_currency, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (portfolio_id, current_user["id"], portfolio.name, portfolio.base_currency, now, now)
        )
        
        # Add base currency cash balance
        conn.execute(
            """INSERT INTO cash_balances (id, portfolio_id, currency, amount, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (secrets.token_urlsafe(16), portfolio_id, portfolio.base_currency, 0, now)
        )
        
        cursor = conn.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
        return PortfolioResponse(**dict(cursor.fetchone()))

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
            (portfolio_id, current_user["id"])
        )
        portfolio = cursor.fetchone()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        # Get positions
        cursor = conn.execute(
            "SELECT * FROM positions WHERE portfolio_id = ?",
            (portfolio_id,)
        )
        positions = {}
        for row in cursor.fetchall():
            pos = dict(row)
            positions[pos["figi"]] = PositionResponse(**pos)
        
        # Get cash balances
        cursor = conn.execute(
            "SELECT * FROM cash_balances WHERE portfolio_id = ?",
            (portfolio_id,)
        )
        cash_balances = {row["currency"]: row["amount"] for row in cursor.fetchall()}
        
        portfolio_dict = dict(portfolio)
        portfolio_dict["positions"] = positions
        portfolio_dict["cash_balances"] = cash_balances
        
        return PortfolioResponse(**portfolio_dict)

@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: str, 
    name: str, 
    current_user = Depends(get_current_user), 
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "UPDATE portfolios SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (name, datetime.utcnow(), portfolio_id, current_user["id"])
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        cursor = conn.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
        return PortfolioResponse(**dict(cursor.fetchone()))

@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(portfolio_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "DELETE FROM portfolios WHERE id = ? AND user_id = ?",
            (portfolio_id, current_user["id"])
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Portfolio not found")

# Positions
@router.get("/{portfolio_id}/positions", response_model=List[PositionResponse])
async def get_positions(portfolio_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
            (portfolio_id, current_user["id"])
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        cursor = conn.execute(
            "SELECT * FROM positions WHERE portfolio_id = ?",
            (portfolio_id,)
        )
        return [PositionResponse(**dict(row)) for row in cursor.fetchall()]

@router.post("/{portfolio_id}/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def add_position(
    portfolio_id: str,
    position: PositionBase,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
            (portfolio_id, current_user["id"])
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        position_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        conn.execute(
            """INSERT INTO positions (id, portfolio_id, figi, quantity, avg_cost, currency, opened_at, last_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (position_id, portfolio_id, position.figi, position.quantity, 
             position.avg_cost, position.currency, now, now)
        )
        
        cursor = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        return PositionResponse(**dict(cursor.fetchone()))

@router.delete("/{portfolio_id}/positions/{figi}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_position(portfolio_id: str, figi: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "DELETE FROM positions WHERE portfolio_id = ? AND figi = ?",
            (portfolio_id, figi)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Position not found")

# Transactions
@router.get("/{portfolio_id}/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    portfolio_id: str,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
            (portfolio_id, current_user["id"])
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        query = "SELECT * FROM transactions WHERE portfolio_id = ?"
        params = [portfolio_id]
        
        if start:
            query += " AND executed_at >= ?"
            params.append(start)
        if end:
            query += " AND executed_at <= ?"
            params.append(end)
        
        query += " ORDER BY executed_at DESC"
        
        cursor = conn.execute(query, params)
        return [TransactionResponse(**dict(row)) for row in cursor.fetchall()]

@router.post("/{portfolio_id}/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_transaction(
    portfolio_id: str,
    transaction: TransactionBase,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
            (portfolio_id, current_user["id"])
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        trans_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        conn.execute(
            """INSERT INTO transactions (id, portfolio_id, figi, side, quantity, price, price_currency, 
               fees, fees_currency, slippage, slippage_currency, executed_at, status, broker, order_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trans_id, portfolio_id, transaction.figi, transaction.side, transaction.quantity,
             transaction.price, transaction.price_currency, transaction.fees, transaction.fees_currency,
             transaction.slippage, transaction.slippage_currency, transaction.executed_at,
             transaction.status, transaction.broker, transaction.order_id, now)
        )
        
        cursor = conn.execute("SELECT * FROM transactions WHERE id = ?", (trans_id,))
        return TransactionResponse(**dict(cursor.fetchone()))

import secrets