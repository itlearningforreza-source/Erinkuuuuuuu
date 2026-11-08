from .auth import router as auth_router
from .market_data import router as market_data_router
from .instruments import router as instruments_router
from .watchlists import router as watchlists_router
from .companies import router as companies_router
from .valuation import router as valuation_router
from .portfolio import router as portfolio_router
from .risk import router as risk_router
from .fixed_income import router as fixed_income_router
from .derivatives import router as derivatives_router
from .workspace import router as workspace_router
from .ai import router as ai_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "market_data_router",
    "instruments_router",
    "watchlists_router",
    "companies_router",
    "valuation_router",
    "portfolio_router",
    "risk_router",
    "fixed_income_router",
    "derivatives_router",
    "workspace_router",
    "ai_router",
    "admin_router",
]