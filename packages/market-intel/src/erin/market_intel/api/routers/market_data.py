"""Market Data Router."""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from erin.core.exceptions import NotFoundError, ValidationError
from erin.market_intel.domain.interfaces import (
    InstrumentId,
    Quote,
    Bar,
    DataFrequency,
    ProviderId,
)

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.get("/quotes", response_model=List[Quote])
async def get_quotes(
    symbols: List[str] = Query(..., description="Comma-separated list of symbols"),
    fields: Optional[List[str]] = Query(None, description="Fields to return"),
):
    """Get real-time quotes for symbols."""
    # This would integrate with the market data service
    # For now, return mock data
    quotes = []
    for symbol in symbols:
        quotes.append({
            "instrument_id": {
                "figi": f"FIGI_{symbol}",
                "composite_ticker": symbol,
                "provider_symbol": symbol
            },
            "bid": {"value": 150.0, "currency": "USD", "timestamp": datetime.utcnow().isoformat(), "source": "MOCK"},
            "ask": {"value": 150.5, "currency": "USD", "timestamp": datetime.utcnow().isoformat(), "source": "MOCK"},
            "last": {"value": 150.25, "currency": "USD", "timestamp": datetime.utcnow().isoformat(), "source": "MOCK"},
            "volume": 1000000,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "MOCK"
        })
    return quotes


@router.get("/quotes/{symbol}", response_model=Quote)
async def get_quote(
    symbol: str,
    fields: Optional[List[str]] = Query(None),
):
    """Get real-time quote for a single symbol."""
    # Mock implementation
    return {
        "instrument_id": {
            "figi": f"FIGI_{symbol}",
            "composite_ticker": symbol,
            "provider_symbol": symbol
        },
        "bid": {"value": 150.0, "currency": "USD", "timestamp": datetime.utcnow().isoformat(), "source": "MOCK"},
        "ask": {"value": 150.5, "currency": "USD", "timestamp": datetime.utcnow().isoformat(), "source": "MOCK"},
        "last": {"value": 150.25, "currency": "USD", "timestamp": datetime.utcnow().isoformat(), "source": "MOCK"},
        "volume": 1000000,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "MOCK"
    }


@router.get("/history", response_model=List[dict])
async def get_history(
    symbol: str = Query(..., description="Symbol to fetch history for"),
    start: datetime = Query(..., description="Start date"),
    end: datetime = Query(None, description="End date"),
    frequency: str = Query("1d", description="Data frequency"),
    adjustment: str = Query("none", description="Adjustment type"),
):
    """Get historical price data."""
    # Mock implementation
    return [
        {
            "timestamp": (datetime.utcnow() - timedelta(days=i)).isoformat(),
            "open": 150.0 + i * 0.1,
            "high": 151.0 + i * 0.1,
            "low": 149.0 + i * 0.1,
            "close": 150.5 + i * 0.1,
            "volume": 1000000 + i * 10000,
        }
        for i in range(30)
    ]


@router.get("/instruments/search")
async def search_instruments(
    query: str = Query(..., description="Search query"),
    asset_class: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Search for instruments."""
    # Mock implementation
    return [
        {
            "figi": "FIGI_AAPL",
            "composite_ticker": "AAPL",
            "provider_symbol": "AAPL"
        },
        {
            "figi": "FIGI_MSFT",
            "composite_ticker": "MSFT",
            "provider_symbol": "MSFT"
        }
    ]


@router.get("/instruments/{symbol}")
async def get_instrument(symbol: str):
    """Get instrument details."""
    return {
        "figi": f"FIGI_{symbol}",
        "composite_ticker": symbol,
        "name": f"{symbol} Inc.",
        "asset_class": "EQUITY",
        "exchange": "NASDAQ",
        "currency": "USD",
        "country": "US",
    }