"""News Router."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta


router = APIRouter(tags=["News"])


@router.get("/")
async def get_news(
    tickers: Optional[List[str]] = Query(None),
    categories: Optional[List[str]] = Query(None),
    sources: Optional[List[str]] = Query(None),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get news articles."""
    return [
        {
            "id": "news_1",
            "title": "Apple Reports Record Q4 Earnings",
            "summary": "Apple beats earnings expectations with strong iPhone sales...",
            "content": "Apple Inc. reported quarterly earnings that beat analyst expectations...",
            "url": "https://example.com/news/1",
            "source": "Reuters",
            "published_at": "2024-01-15T10:30:00Z",
            "categories": ["EARNINGS", "TECHNOLOGY"],
            "tickers": ["AAPL"],
            "sentiment": "POSITIVE",
            "sentiment_score": 0.75,
            "relevance_score": 0.95,
        },
        {
            "id": "news_2",
            "title": "Fed Holds Rates Steady, Signals Rate Cuts in 2024",
            "summary": "Federal Reserve keeps rates unchanged but signals potential cuts...",
            "content": "The Federal Reserve held interest rates steady...",
            "url": "https://example.com/news/2",
            "source": "Bloomberg",
            "published_at": "2024-01-15T14:00:00Z",
            "categories": ["ECONOMY", "MONETARY_POLICY"],
            "tickers": ["SPY", "TLT"],
            "sentiment": "NEUTRAL",
            "sentiment_score": 0.1,
            "relevance_score": 0.85,
        }
    ]


@router.get("/{news_id}")
async def get_news_article(news_id: str):
    """Get a specific news article."""
    return {
        "id": "news_1",
        "title": "Apple Reports Record Q4 Earnings",
        "summary": "Apple beats earnings expectations with strong iPhone sales...",
        "content": "Apple Inc. reported quarterly earnings that beat analyst expectations...",
        "url": "https://example.com/news/1",
        "source": "Reuters",
        "published_at": "2024-01-15T10:30:00Z",
        "categories": ["EARNINGS", "TECHNOLOGY"],
        "tickers": ["AAPL"],
        "sentiment": "POSITIVE",
        "sentiment_score": 0.75,
        "relevance_score": 0.95,
    }


@router.get("/sentiment/{ticker}")
async def get_sentiment(
    ticker: str,
    hours: int = Query(24, ge=1, le=168),
):
    """Get sentiment analysis for a ticker."""
    return {
        "ticker": "AAPL",
        "period_hours": 24,
        "article_count": 45,
        "sentiment_score": 0.65,
        "sentiment_label": "POSITIVE",
        "positive_articles": 28,
        "negative_articles": 12,
        "neutral_articles": 5,
        "top_keywords": ["earnings", "iphone", "services", "china", "growth"],
        "sentiment_trend": "IMPROVING",
    }


@router.get("/trending")
async def get_trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
):
    """Get trending topics and tickers."""
    return {
        "keywords": [
            {"keyword": "earnings", "count": 120, "sentiment": 0.6},
            {"keyword": "fed", "count": 95, "sentiment": -0.2},
            {"keyword": "ai", "count": 85, "sentiment": 0.8},
            {"keyword": "inflation", "count": 70, "sentiment": -0.3},
            {"keyword": "rates", "count": 65, "sentiment": -0.4},
        ],
        "tickers": [
            {"ticker": "AAPL", "count": 45, "sentiment": 0.7},
            {"ticker": "NVDA", "count": 42, "sentiment": 0.8},
            {"ticker": "TSLA", "count": 38, "sentiment": 0.3},
            {"ticker": "MSFT", "count": 35, "sentiment": 0.6},
            {"ticker": "GOOGL", "count": 30, "sentiment": 0.4},
        ],
    }