"""Fundamentals Router."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal


router = APIRouter(prefix="/fundamentals", tags=["Fundamentals"])


@router.get("/company/{symbol}")
async def get_company_profile(symbol: str):
    """Get company profile."""
    return {
        "symbol": symbol,
        "name": f"{symbol} Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "country": "US",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "description": f"{symbol} Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.",
        "website": f"https://www.{symbol.lower()}.com",
        "employees": 164000,
        "market_cap": 2500000000000,
        "shares_outstanding": 15000000000,
        "float_shares": 14000000000,
        "ceo": "Tim Cook",
        "headquarters": "Cupertino, CA, USA",
        "founded": "1976-04-01",
    }


@router.get("/{symbol}/financials")
async def get_financials(
    symbol: str,
    statement_type: str = Query("income", regex="^(income|balance|cashflow)$"),
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    limit: int = Query(10, ge=1, le=20),
):
    """Get financial statements."""
    return {
        "symbol": "AAPL",
        "statement_type": "income",
        "period_type": "annual",
        "currency": "USD",
        "filings": [
            {
                "period_end": "2023-09-30",
                "fiscal_year": 2023,
                "fiscal_period": "FY",
                "revenue": 383285000000,
                "gross_profit": 169148000000,
                "operating_income": 114301000000,
                "net_income": 96995000000,
                "eps_basic": 6.13,
                "eps_diluted": 6.11,
                "shares_outstanding": 15500000000,
            },
            {
                "period_end": "2022-09-24",
                "fiscal_year": 2022,
                "fiscal_period": "FY",
                "revenue": 394328000000,
                "gross_profit": 170782000000,
                "operating_income": 119437000000,
                "net_income": 99803000000,
                "eps_basic": 6.15,
                "eps_diluted": 6.11,
                "shares_outstanding": 16000000000,
            },
        ]
    }


@router.get("/{symbol}/ratios")
async def get_ratios(
    symbol: str,
    period: str = Query("annual", regex="^(annual|quarterly|ttm)$"),
    limit: int = Query(10, ge=1, le=20),
):
    """Get financial ratios."""
    return {
        "symbol": "AAPL",
        "period": "annual",
        "ratios": [
            {
                "period_end": "2023-09-30",
                "pe_ratio": 28.5,
                "pb_ratio": 45.2,
                "ps_ratio": 7.8,
                "ev_ebitda": 22.1,
                "roe": 1.47,
                "roa": 0.27,
                "roe_adj": 1.47,
                "roic": 0.52,
                "gross_margin": 0.44,
                "operating_margin": 0.30,
                "net_margin": 0.25,
                "current_ratio": 1.07,
                "quick_ratio": 0.92,
                "debt_to_equity": 1.73,
                "debt_to_ebitda": 1.2,
                "interest_coverage": 28.5,
                "fcf_yield": 0.035,
                "dividend_yield": 0.005,
                "payout_ratio": 0.15,
            }
        ]
    }


@router.get("/{symbol}/estimates")
async def get_estimates(
    symbol: str,
    period: str = Query("next_quarter", regex="^(next_quarter|next_year|current_year)$"),
):
    """Get analyst estimates."""
    return {
        "symbol": "AAPL",
        "period": "next_quarter",
        "estimates": {
            "revenue": {"mean": 118.5, "high": 120.0, "low": 117.0, "count": 28},
            "eps": {"mean": 2.15, "high": 2.20, "low": 2.10, "count": 30},
        },
        "consensus_rating": "BUY",
        "price_target": {"mean": 195.0, "high": 220.0, "low": 170.0, "count": 35},
    }


@router.get("/{symbol}/dividends")
async def get_dividends(
    symbol: str,
    limit: int = Query(20, ge=1, le=50),
):
    """Get dividend history."""
    return {
        "symbol": "AAPL",
        "dividends": [
            {
                "ex_date": "2024-02-09",
                "pay_date": "2024-02-15",
                "amount": 0.24,
                "currency": "USD",
                "type": "quarterly",
            },
            {
                "ex_date": "2023-11-10",
                "pay_date": "2023-11-16",
                "amount": 0.24,
                "currency": "USD",
                "type": "quarterly",
            },
        ],
        "dividend_yield": 0.005,
        "payout_ratio": 0.15,
        "years_of_growth": 12,
    }


@router.get("/{symbol}/splits")
async def get_splits(symbol: str):
    """Get stock split history."""
    return {
        "symbol": "AAPL",
        "splits": [
            {
                "date": "2020-08-31",
                "ratio": "4:1",
                "description": "4-for-1 stock split",
            },
            {
                "date": "2014-06-09",
                "ratio": "7:1",
                "description": "7-for-1 stock split",
            },
        ],
    }