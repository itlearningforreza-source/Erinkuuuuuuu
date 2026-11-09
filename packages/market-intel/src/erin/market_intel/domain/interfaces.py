"""Market Data Provider Interfaces - Core abstractions for market data providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator
from enum import Enum
import asyncio


class ProviderId(str, Enum):
    """Supported market data providers."""
    OPENBB = "openbb"
    YFINANCE = "yfinance"
    FRED = "fred"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    TWELVE_DATA = "twelve_data"
    MANUAL = "manual"
    SEC_EDGAR = "sec_edgar"


class AssetClass(str, Enum):
    """Financial asset classes."""
    EQUITY = "EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    DERIVATIVE = "DERIVATIVE"
    COMMODITY = "COMMODITY"
    FX = "FX"
    CRYPTO = "CRYPTO"
    FUND = "FUND"
    CASH = "CASH"


class DataFrequency(str, Enum):
    """Data frequency/granularity."""
    TICK = "tick"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class CurrencyCode(str, Enum):
    """ISO 4217 currency codes."""
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    CNY = "CNY"
    IDR = "IDR"
    # Add more as needed


@dataclass(frozen=True)
class InstrumentId:
    """Canonical instrument identifier."""
    figi: str                    # Primary: OpenFIGI
    composite_ticker: str        # e.g., "AAPL.US", "7203.T"
    provider_symbol: Optional[str] = None  # Provider-specific symbol


@dataclass(frozen=True)
class Price:
    """Price with metadata."""
    value: Decimal
    currency: str
    timestamp: datetime
    source: ProviderId


@dataclass
class Quote:
    """Real-time quote."""
    instrument_id: InstrumentId
    bid: Optional[Price]
    ask: Optional[Price]
    last: Optional[Price]
    bid_size: Optional[int]
    ask_size: Optional[int]
    volume: Optional[int]
    timestamp: datetime
    source: ProviderId

    @property
    def mid(self) -> Optional[Decimal]:
        """Mid price (bid + ask) / 2."""
        if self.bid and self.ask:
            return (self.bid.value + self.ask.value) / Decimal('2')
        return None

    @property
    def spread(self) -> Optional[Decimal]:
        """Bid-ask spread."""
        if self.bid and self.ask:
            return self.ask.value - self.bid.value
        return None


@dataclass
class Bar:
    """OHLCV bar/candle."""
    instrument_id: InstrumentId
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    frequency: DataFrequency
    source: ProviderId
    adjustment: str = "none"  # none, split, dividend, all


@dataclass
class MarketCalendar:
    """Market trading calendar."""
    exchange: str
    year: int
    trading_days: List[datetime]
    holidays: List[Dict[str, Any]]
    early_closes: List[Dict[str, Any]]


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""

    @property
    @abstractmethod
    def provider_id(self) -> ProviderId:
        """Unique provider identifier."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def supported_asset_classes(self) -> List[AssetClass]:
        """Asset classes this provider supports."""
        pass

    @property
    @abstractmethod
    def supported_frequencies(self) -> List[DataFrequency]:
        """Data frequencies this provider supports."""
        pass

    @property
    @abstractmethod
    def rate_limit(self) -> Dict[str, int]:
        """Rate limits: requests_per_minute, burst."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider availability."""
        pass

    @abstractmethod
    async def search_instruments(
        self,
        query: str,
        asset_class: Optional[AssetClass] = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ) -> List[InstrumentId]:
        """Search instruments by symbol, name, or FIGI."""
        pass

    @abstractmethod
    async def get_instrument(self, instrument_id: InstrumentId) -> Optional[Dict[str, Any]]:
        """Get instrument metadata."""
        pass

    @abstractmethod
    async def get_quotes(
        self,
        symbols: List[str],
        fields: Optional[List[str]] = None
    ) -> Dict[str, Quote]:
        """Get real-time quotes for symbols."""
        pass

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: DataFrequency = DataFrequency.DAY,
        adjustment: str = "none"
    ) -> List[Bar]:
        """Get historical price data."""
        pass

    @abstractmethod
    async def subscribe_quotes(
        self,
        symbols: List[str],
        callback: callable
    ) -> AsyncIterator[Quote]:
        """Subscribe to real-time quote stream."""
        pass

    @abstractmethod
    async def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Unsubscribe from quote stream."""
        pass

    @abstractmethod
    async def get_calendar(
        self,
        exchange: str,
        year: int
    ) -> MarketCalendar:
        """Get market calendar for exchange."""
        pass

    @abstractmethod
    def supports_real_time(self) -> bool:
        """Whether provider supports real-time streaming."""
        pass

    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether provider requires API key."""
        pass


class ProviderRegistry:
    """Registry for managing market data providers."""

    def __init__(self):
        self._providers: Dict[ProviderId, MarketDataProvider] = {}
        self._default_provider: Optional[ProviderId] = None

    def register(self, provider: MarketDataProvider, set_default: bool = False) -> None:
        """Register a provider."""
        self._providers[provider.provider_id] = provider
        if set_default or self._default_provider is None:
            self._default_provider = provider.provider_id

    def unregister(self, provider_id: ProviderId) -> None:
        """Unregister a provider."""
        self._providers.pop(provider_id, None)
        if self._default_provider == provider_id:
            self._default_provider = next(iter(self._providers), None)

    def get(self, provider_id: ProviderId) -> Optional[MarketDataProvider]:
        """Get provider by ID."""
        return self._providers.get(provider_id)

    def get_default(self) -> Optional[MarketDataProvider]:
        """Get default provider."""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        return next(iter(self._providers.values()), None)

    def list_providers(self) -> List[MarketDataProvider]:
        """List all registered providers."""
        return list(self._providers.values())

    def get_by_asset_class(self, asset_class: AssetClass) -> List[MarketDataProvider]:
        """Get providers supporting an asset class."""
        return [
            p for p in self._providers.values()
            if asset_class in p.supported_asset_classes
        ]