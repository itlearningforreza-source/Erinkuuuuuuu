from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_duckdb_db, get_sqlite_db, sqlite_transaction
from erin.api.core.config import settings
from erin.api.models.market_data import Quote, QuoteBatch, Bar, Instrument, InstrumentSearch

router = APIRouter(prefix="/api/v1/quotes", tags=["market-data"])

@router.get("", response_model=dict)
async def get_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to return"),
    db = Depends(get_sqlite_db)
):
    """Get real-time quotes for symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    with sqlite_transaction() as conn:
        placeholders = ",".join(["?"] * len(symbols_list))
        cursor = conn.execute(
            f"""SELECT i.figi, i.composite_ticker, i.name, i.currency, i.asset_class
                FROM instruments i
                WHERE i.composite_ticker IN ({placeholders})""",
            symbols_list
        )
        instruments = {row["composite_ticker"]: dict(row) for row in cursor.fetchall()}
    
    # In a real implementation, this would query the real-time quote cache
    # For now, return mock data structure
    quotes = {}
    for symbol in symbols_list:
        if symbol in instruments:
            quotes[symbol] = {
                "symbol": symbol,
                "bid": 150.01,
                "ask": 150.02,
                "last": 150.015,
                "bid_size": 100,
                "ask_size": 100,
                "volume": 1000000,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "openbb",
                "currency": instruments[symbol]["currency"]
            }
    
    return {"quotes": quotes}

@router.get("/{figi}/history")
async def get_quote_history(
    figi: str,
    start: date = Query(...),
    end: date = Query(...),
    interval: str = "1d",
    adjustment: str = "none",
    db = Depends(get_duckdb_db)
):
    """Get historical price data for an instrument."""
    # Query adjusted_quotes table
    query = """
        SELECT timestamp, adj_open as open, adj_high as high, adj_low as low, adj_close as close, adj_volume as volume
        FROM adjusted_quotes
        WHERE figi = ? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    """
    result = db.execute(query, [figi, start.isoformat(), end.isoformat()]).fetchall()
    
    bars = [
        {
            "time": int(row[0].timestamp()) if hasattr(row[0], 'timestamp') else row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5]
        }
        for row in result
    ]
    
    return {"symbol": figi, "interval": interval, "bars": bars}

@router.websocket("/ws/quotes")
async def websocket_quotes(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "subscribe":
                symbols = data.get("symbols", [])
                # Subscribe to quote updates
                # In real implementation, this would subscribe to a Redis pub/sub
                await websocket.send_json({"type": "subscribed", "symbols": symbols})
            elif data.get("action") == "unsubscribe":
                symbols = data.get("symbols", [])
                await websocket.send_json({"type": "unsubscribed", "symbols": symbols})
    except Exception:
        await websocket.close()

from fastapi import WebSocket