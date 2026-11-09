"""OpenBB Provider Adapter - Wraps OpenBB Platform for market data."""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from openbb import OpenBB

from erin.market_intel.domain.interfaces import (
    MarketDataProvider,
    ProviderId,
    AssetClass,
    DataFrequency,
    InstrumentId,
    Quote,
    Price,
    Bar,
    MarketCalendar,
    MarketDataProvider,
    ProviderRegistry,
)

logger = logging.getLogger(__name__)


class OpenBBProvider(MarketDataProvider):
    """OpenBB Platform market data provider adapter."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:6900",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self._api_base_url = api_base_url.rstrip('/')
        self._api_key = api_key
        self._timeout = timeout
        self._client = None
        self._ws_connections: Dict[str, asyncio.Task] = {}
        self._quote_callbacks: Dict[str, List[callable]] = {}

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId.OPENBB

    @property
    def name(self) -> str:
        return "OpenBB Platform"

    @property
    def supported_asset_classes(self) -> List[AssetClass]:
        return [
            AssetClass.EQUITY,
            AssetClass.FIXED_INCOME,
            AssetClass.DERIVATIVE,
            AssetClass.COMMODITY,
            AssetClass.FX,
            AssetClass.CRYPTO,
            AssetClass.FUND,
        ]

    @property
    def supported_frequencies(self) -> List[DataFrequency]:
        return [
            DataFrequency.MINUTE,
            DataFrequency.HOUR,
            DataFrequency.DAY,
            DataFrequency.WEEK,
            DataFrequency.MONTH,
        ]

    @property
    def rate_limit(self) -> Dict[str, int]:
        return {"requests_per_minute": 60, "burst": 10}

    async def _get_client(self):
        """Lazy-load OpenBB client."""
        if self._client is None:
            try:
                from openbb import OpenBB
                self._client = OpenBB()
                logger.info("OpenBB client initialized")
            except ImportError:
                logger.error("OpenBB not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize OpenBB client: {e}")
                raise
        return self._client

    async def health_check(self) -> bool:
        """Check if OpenBB API is accessible."""
        try:
            client = await self._get_client()
            # Simple health check - try to get a quote
            result = client.equity.price.historical("AAPL", start_date="2024-01-01", end_date="2024-01-02")
            return result is not None and len(result) > 0
        except Exception as e:
            logger.warning(f"OpenBB health check failed: {e}")
            return False

    def _map_frequency(self, freq: DataFrequency) -> str:
        """Map DataFrequency to OpenBB interval."""
        mapping = {
            DataFrequency.MINUTE: "1m",
            DataFrequency.HOUR: "1h",
            DataFrequency.DAY: "1d",
            DataFrequency.WEEK: "1wk",
            DataFrequency.MONTH: "1mo",
        }
        return mapping.get(freq, "1d")

    def _to_instrument_id(self, symbol: str) -> InstrumentId:
        """Convert symbol to InstrumentId."""
        # In real implementation, would look up FIGI from instrument master
        return InstrumentId(
            figi=f"FIGI_{symbol}",
            composite_ticker=symbol,
            provider_symbol=symbol
        )

    def _to_quote(self, symbol: str, data: Dict[str, Any]) -> Quote:
        """Convert OpenBB quote data to Quote."""
        instrument_id = self._to_instrument_id(symbol)
        now = datetime.utcnow()
        
        return Quote(
            instrument_id=instrument_id,
            bid=Price(Decimal(str(data.get('bid', 0))), 'USD', now, ProviderId.OPENBB) if data.get('bid') else None,
            ask=Price(Decimal(str(data.get('ask', 0))), 'USD', now, ProviderId.OPENBB) if data.get('ask') else None,
            last=Price(Decimal(str(data.get('last', data.get('close', 0)))), 'USD', now, ProviderId.OPENBB) if data.get('last') or data.get('close') else None,
            bid_size=data.get('bid_size'),
            ask_size=data.get('ask_size'),
            volume=data.get('volume'),
            timestamp=now,
            source=ProviderId.OPENBB
        )

    def _to_bar(self, symbol: str, row: Any, freq: DataFrequency) -> Bar:
        """Convert OpenBB historical row to Bar."""
        instrument_id = self._to_instrument_id(symbol)
        
        # Handle different row formats (DataFrame row, dict, etc.)
        if hasattr(row, 'to_dict'):
            data = row.to_dict()
        elif isinstance(row, dict):
            data = row
        else:
            data = dict(row)
        
        return Bar(
            instrument_id=instrument_id,
            timestamp=pd.Timestamp(data.get('date', data.get('Date'))).to_pydatetime() if 'date' in data or 'Date' in data else datetime.utcnow(),
            open=Decimal(str(data.get('open', data.get('Open', 0)))),
            high=Decimal(str(data.get('high', data.get('High', 0)))),
            low=Decimal(str(data.get('low', data.get('Low', 0)))),
            close=Decimal(str(data.get('close', data.get('Close', 0)))),
            volume=int(data.get('volume', data.get('Volume', 0))),
            frequency=DataFrequency.DAY,  # Default, would map from freq
            source=ProviderId.OPENBB,
            adjustment="none"
        )

    async def search_instruments(
        self,
        query: str,
        asset_class: Optional[AssetClass] = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ) -> List[InstrumentId]:
        """Search instruments via OpenBB."""
        try:
            client = await self._get_client()
            # OpenBB doesn't have a direct search endpoint, use equity search
            results = client.equity.search(query, limit=limit)
            
            instruments = []
            for _, row in results.iterrows():
                symbol = row.get('symbol', row.get('Symbol', ''))
                if symbol:
                    instruments.append(InstrumentId(
                        figi=f"FIGI_{symbol}",
                        composite_ticker=symbol,
                        provider_symbol=symbol
                    ))
            return instruments[:limit]
        except Exception as e:
            logger.error(f"OpenBB instrument search failed: {e}")
            return []

    async def get_instrument(self, instrument_id: InstrumentId) -> Optional[Dict[str, Any]]:
        """Get instrument metadata from OpenBB."""
        try:
            client = await self._get_client()
            symbol = instrument_id.composite_ticker
            profile = client.equity.profile(symbol)
            return profile.to_dict() if hasattr(profile, 'to_dict') else dict(profile)
        except Exception as e:
            logger.error(f"OpenBB get_instrument failed: {e}")
            return None

    async def get_quotes(
        self,
        symbols: List[str],
        fields: Optional[List[str]] = None
    ) -> Dict[str, Quote]:
        """Get real-time quotes for symbols."""
        try:
            client = await self._get_client()
            quotes = {}
            
            for symbol in symbols:
                try:
                    quote_data = client.equity.price.quote(symbol)
                    if quote_data is not None:
                        quotes[symbol] = self._to_quote(symbol, quote_data)
                except Exception as e:
                    logger.warning(f"Failed to get quote for {symbol}: {e}")
                    
            return quotes
        except Exception as e:
            logger.error(f"OpenBB get_quotes failed: {e}")
            return {}

    async def get_history(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: DataFrequency = DataFrequency.DAY,
        adjustment: str = "none"
    ) -> List[Bar]:
        """Get historical price data."""
        try:
            client = await self._get_client()
            interval = self._map_frequency(frequency)
            
            # OpenBB historical data
            data = client.equity.price.historical(
                symbol,
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                interval=interval
            )
            
            bars = []
            if data is not None and len(data) > 0:
                for _, row in data.iterrows():
                    bars.append(self._to_bar(symbol, row, frequency))
                    
            return bars
        except Exception as e:
            logger.error(f"OpenBB get_history failed: {e}")
            return []

    async def get_calendar(
        self,
        exchange: str,
        year: int
    ) -> MarketCalendar:
        """Get market calendar."""
        try:
            client = await self._get_client()
            # OpenBB doesn't have direct calendar endpoint
            # Return basic calendar
            return MarketCalendar(
                exchange=exchange,
                year=year,
                trading_days=[],  # Would need to compute
                holidays=[],
                early_closes=[]
            )
        except Exception as e:
            logger.error(f"OpenBB get_calendar failed: {e}")
            return MarketCalendar(exchange=exchange, year=year, trading_days=[], holidays=[], early_closes=[])

    def supports_real_time(self) -> bool:
        return False  # OpenBB doesn't support native real-time streaming

    def requires_api_key(self) -> bool:
        return False  # OpenBB runs locally

    def _map_frequency(self, freq: DataFrequency) -> str:
        mapping = {
            DataFrequency.MINUTE: "1m",
            DataFrequency.HOUR: "1h",
            DataFrequency.DAY: "1d",
            DataFrequency.WEEK: "1wk",
            DataFrequency.MONTH: "1mo",
        }
        return mapping.get(freq, "1d")

    def _to_bar(self, symbol: str, row: Any, freq: DataFrequency) -> Bar:
        instrument_id = self._to_instrument_id(symbol)
        
        if hasattr(row, 'to_dict'):
            data = row.to_dict()
        elif isinstance(row, dict):
            data = row
        else:
            data = dict(row)
        
        date_val = data.get('date', data.get('Date', datetime.utcnow()))
        if isinstance(date_val, str):
            timestamp = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
        else:
            timestamp = date_val
            
        return Bar(
            instrument_id=instrument_id,
            timestamp=timestamp,
            open=Decimal(str(data.get('open', data.get('Open', 0)))),
            high=Decimal(str(data.get('high', data.get('High', 0)))),
            low=Decimal(str(data.get('low', data.get('Low', 0)))),
            close=Decimal(str(data.get('close', data.get('Close', 0)))),
            volume=int(data.get('volume', data.get('Volume', 0))),
            frequency=DataFrequency.DAY,
            source=ProviderId.OPENBB,
            adjustment="none"
        )

    async def subscribe_quotes(
        self,
        symbols: List[str],
        callback: callable
    ) -> AsyncIterator[Quote]:
        """Subscribe to real-time quotes (polling fallback)."""
        # OpenBB doesn't support native WebSocket streaming
        # Fallback to polling
        interval = 5  # seconds
        
        while True:
            try:
                quotes = await self.get_quotes(symbols)
                for symbol, quote in quotes.items():
                    await callback(quote)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Quote polling error: {e}")
                await asyncio.sleep(5)

    async def unsubscribe_quotes(self, symbols: List[str]) -> None:
        """Unsubscribe from quote stream."""
        # No-op for polling-based implementation
        pass


# Register OpenBB provider
def create_openbb_provider(config: Dict[str, Any]) -> MarketDataProvider:
    """Factory function to create OpenBB provider."""
    return OpenBBProvider(
        api_base_url=config.get('api_base_url', 'http://localhost:6900'),
        api_key=config.get('api_key'),
        timeout=config.get('timeout', 30)
    )


# Register with global registry
def register_openbb(registry: ProviderRegistry, config: Dict[str, Any]) -> None:
    """Register OpenBB provider with registry."""
    provider = create_openbb_provider(config)
    registry.register(provider, set_default=True)