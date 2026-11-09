"""ERIN Market Intelligence - API Module."""

from erin.market_intel.api.main import app
from erin.market_intel.api.routers import (
    market_data,
    instruments,
    watchlists,
    charts,
    portfolios,
    orders,
    risk,
    analytics,
    news,
    fundamentals,
)

__all__ = [
    "app",
    "market_data",
    "instruments",
    "watchlists",
    "charts",
    "portfolios",
    "orders",
    "risk",
    "analytics",
    "news",
    "fundamentals",
]