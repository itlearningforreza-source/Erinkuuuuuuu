"""Instruments Router."""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime

router = APIRouter(tags=["Instruments"])


@router.get("/search")
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
            "name": "Apple Inc.",
            "asset_class": "EQUITY",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
        },
        {
            "figi": "FIGI_MSFT",
            "composite_ticker": "MSFT",
            "name": "Microsoft Corporation",
            "asset_class": "EQUITY",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
        }
    ]


@router.get("/{symbol}")
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
        "sector": "Technology",
        "industry": "Consumer Electronics",
    }


@router.get("/{symbol}/metadata")
async def get_instrument_metadata(symbol: str):
    """Get instrument metadata."""
    return {
        "figi": f"FIGI_{symbol}",
        "composite_ticker": symbol,
        "name": f"{symbol} Inc.",
        "asset_class": "EQUITY",
        "exchange": "NASDAQ",
        "currency": "USD",
        "country": "US",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 2500000000000,
        "shares_outstanding": 15000000000,
        "float_shares": 14000000000,
    }