"""Market Data Service - Central service for all market data operations."""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Dict, AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.market_intel.adapters.base import MarketDataProvider
    from erin.market_intel.domain.interfaces import (
        Quote, Bar, InstrumentId, MarketCalendar,
        ProviderId, DataFrequency
    )

logger = logging.getLogger(__name__)


class MarketDataService:
    """Central service for all market data operations."""
    
    def __init__(
        self,
        provider_registry: 'ProviderRegistry',
        storage: 'SQLiteStorage',
        duckdb_storage: 'DuckDBStorage',
        parquet_storage: 'ParquetStorage'
    ):
        self.provider_registry = provider_registry
        self.storage = storage
        self.duckdb = duckdb_storage
        self.parquet = parquet_storage
        self._quote_cache: Dict[str, Any] = {}
        self._cache_ttl = 5  # seconds
    
    async def get_quotes(
        self,
        symbols: List[str],
        fields: Optional[List[str]] = None,
        provider: Optional[str] = None
    ) -> Dict[str, 'Quote']:
        """Get real-time quotes for symbols."""
        # Try cache first
        cached = {}
        uncached = []
        
        for symbol in symbols:
            cache_key = f"quote:{symbol}"
            if cache_key in self._quote_cache:
                cached[symbol] = self._quote_cache[cache_key]
            else:
                uncached.append(symbol)
        
        if uncached:
            # Use default provider or specified one
            provider_obj = self.provider_registry.get_default()
            if provider:
                provider_obj = self.provider_registry.get(provider)
                if not provider_obj:
                    raise ValueError(f"Provider not found: {provider}")
            
            try:
                quotes = await provider_obj.get_quotes(uncached)
                for symbol, quote in quotes.items():
                    cache_key = f"quote:{symbol}"
                    self._quote_cache[cache_key] = quote
                    cached[symbol] = quote
            except Exception as e:
                logger.error(f"Failed to fetch quotes: {e}")
        
        return cached
    
    async def get_quote_history(
        self,
        figi: str,
        start: date,
        end: date,
        interval: str = "1d",
        adjustment: str = "none",
        provider: Optional[str] = None
    ) -> Dict:
        """Get historical price data for an instrument."""
        provider_obj = self.provider_registry.get_default()
        if provider:
            provider_obj = self.provider_registry.get(provider)
        
        try:
            bars = await self.duckdb.get_history(
                figi=figi,
                start=start,
                end=end,
                interval=interval,
                adjustment=adjustment
            )
            return {"symbol": figi, "interval": interval, "bars": bars}
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return {"symbol": figi, "interval": interval, "bars": []}
    
    async def get_instrument_quotes(self, symbols: List[str]) -> Dict:
        """Get quotes for multiple instruments."""
        return await self.get_quotes(symbols)
    
    async def search_instruments(
        self,
        query: str,
        asset_class: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search instruments by symbol or name."""
        provider = self.provider_registry.get_default()
        return await provider.search_instruments(query, asset_class, exchange, limit)
    
    async def get_instrument(self, figi: str) -> Optional[Dict]:
        """Get instrument metadata."""
        # Check SQLite storage first
        instrument = self.storage.get_instrument(figi)
        if instrument:
            return instrument
        
        # Try to get from provider
        provider = self.provider_registry.get_default()
        return await provider.get_instrument(figi)
    
    async def get_market_calendar(
        self,
        exchange: str,
        year: int
    ) -> Dict:
        """Get market calendar."""
        return await self.storage.get_market_calendar(exchange, year)
    
    async def subscribe_quotes(
        self,
        symbols: List[str],
        callback: callable
    ) -> AsyncIterator:
        """Subscribe to real-time quote updates."""
        provider = self.provider_registry.get_default()
        async for quote in provider.subscribe_quotes(symbols, callback):
            yield quote
    
    # Instrument management
    async def get_instrument(self, figi: str) -> Optional[Dict]:
        return self.storage.get_instrument(figi)
    
    async def search_instruments(
        self,
        search: str = "",
        asset_class: str = "",
        exchange: str = "",
        limit: int = 50
    ) -> List[Dict]:
        provider = self.provider_registry.get_default()
        return await provider.search_instruments(
            search=search,
            asset_class=asset_class,
            exchange=exchange,
            limit=limit
        )