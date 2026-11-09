"""ERIN Market Intelligence - Provider Adapters."""

from erin.market_intel.adapters.base import MarketDataProvider, ProviderConfig
from erin.market_intel.adapters.registry import ProviderRegistry, provider_registry, initialize_provider_registry, DEFAULT_PROVIDER_CONFIGS
from erin.market_intel.adapters.openbb import OpenBBProvider
from erin.market_intel.adapters.yfinance import YFinanceProvider
from erin.market_intel.adapters.fred import FREDProvider
from erin.market_intel.adapters.alpha_vantage import AlphaVantageProvider
from erin.market_intel.adapters.sec_edgar import SECEdgarProvider

__all__ = [
    "MarketDataProvider",
    "ProviderConfig",
    "ProviderRegistry",
    "provider_registry",
    "initialize_provider_registry",
    "DEFAULT_PROVIDER_CONFIGS",
    "OpenBBProvider",
    "YFinanceProvider",
    "FREDProvider",
    "AlphaVantageProvider",
    "SECEdgarProvider",
]