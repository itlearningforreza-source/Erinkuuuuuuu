"""Base classes for market data providers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator
from enum import Enum

from erin.market_intel.domain.interfaces import (
    Quote, Bar, InstrumentId, MarketCalendar,
    ProviderId, AssetClass, DataFrequency
)

logger = logging.getLogger(__name__)


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @property
    @abstractmethod
    def provider_id(self):
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
        """Check if provider is available."""
        pass
    
    @abstractmethod
    async def search_instruments(
        self,
        query: str,
        asset_class: Optional[AssetClass] = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ) -> List[InstrumentId]:
        """Search instruments by query."""
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
    async def get_calendar(
        self,
        exchange: str,
        year: int
    ) -> MarketCalendar:
        """Get market calendar."""
        pass
    
    # These have default implementations - subclasses can override if needed
    def supports_real_time(self) -> bool:
        """Whether provider supports real-time streaming."""
        return False
    
    def requires_api_key(self) -> bool:
        """Whether provider requires API key."""
        return True
    
    async def subscribe_quotes(
        self,
        symbols: List[str],
        callback: callable
    ) -> AsyncIterator[Quote]:
        """Subscribe to real-time quotes."""
        # Default implementation uses polling
        while True:
            try:
                quotes = await self.get_quotes(symbols)
                for quote in quotes.values():
                    await callback(quote)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Quote polling error: {e}")
                await asyncio.sleep(5)

    async def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Unsubscribe from quotes."""
        pass


@dataclass
class ProviderConfig:
    """Provider configuration."""
    provider_id: str
    name: str
    class_name: str
    module_path: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0