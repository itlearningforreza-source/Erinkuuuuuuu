"""ERIN Market Intelligence - API Module."""

from erin.market_intel.api.main import app, create_app
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
    "create_app",
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