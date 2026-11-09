"""Alpha Vantage Provider Adapter - Additional equity/forex/crypto data."""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator, TYPE_CHECKING
import aiohttp

if TYPE_CHECKING:
    pass

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
)

logger = logging.getLogger(__name__)


class AlphaVantageProvider:
    """Alpha Vantage API provider adapter."""

    def __init__(self, api_key: str, timeout: int = 30):
        self._api_key = api_key
        self._timeout = timeout
        self._base_url = "https://www.alphavantage.co/query"
        self._session = None

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.ALPHA_VANTAGE

    @property
    def name(self) -> str:
        return "Alpha Vantage"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY, AssetClass.FX, AssetClass.CRYPTO]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.MINUTE, DataFrequency.HOUR, DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 5, "burst": 1}  # Free tier: 5 req/min

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.ALPHA_VANTAGE

    @property
    def name(self) -> str:
        return "Alpha Vantage"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY, AssetClass.FX, AssetClass.CRYPTO]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.MINUTE, DataFrequency.HOUR, DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 5, "burst": 1}

    async def health_check(self) -> bool:
        try:
            async with self._get_session() as session:
                async with session.get(
                    f"https://www.alphavantage.co/query",
                    params={"function": "GLOBAL_QUOTE", "symbol": "AAPL", "apikey": self._api_key}
                ) as resp:
                    data = await resp.json()
                    return "Global Quote" in data
        except Exception as e:
            logger.warning(f"Alpha Vantage health check failed: {e}")
            return False

    async def _request(self, params: Dict[str, Any]) -> Dict:
        async with self._get_session() as session:
            params["apikey"] = self._api_key
            async with session.get(self._base_url, params=params) as resp:
                return await resp.json()

    async def health_check(self) -> bool:
        try:
            data = await self._request({"function": "GLOBAL_QUOTE", "symbol": "AAPL"})
            return "Global Quote" in data
        except Exception as e:
            logger.warning(f"Alpha Vantage health check failed: {e}")
            return False

    async def search_instruments(
        self,
        query: str,
        asset_class: Optional = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ):
        try:
            data = await self._request({
                "function": "SYMBOL_SEARCH",
                "keywords": query
            })
            
            instruments = []
            for match in data.get("bestMatches", [])[:limit]:
                instruments.append(InstrumentId(
                    figi=f"AV_{match['1. symbol']}",
                    composite_ticker=match['1. symbol'],
                    provider_symbol=match['1. symbol']
                ))
            return instruments[:50]
        except Exception as e:
            logger.error(f"Alpha Vantage search failed: {e}")
            return []

    async def get_instrument(self, instrument_id):
        try:
            data = await self._request({
                "function": "OVERVIEW",
                "symbol": instrument_id.composite_ticker
            })
            return data if data else None
        except Exception as e:
            logger.error(f"Alpha Vantage get_instrument failed: {e}")
            return None

    async def get_quotes(self, symbols: List[str], fields: Optional[List[str]] = None):
        quotes = {}
        for symbol in symbols:
            try:
                data = await self._request({
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol
                })
                
                quote_data = data.get("Global Quote", {})
                if quote_data:
                    from erin.market_intel.domain.interfaces import Quote, Price, InstrumentId, ProviderId
                    from decimal import Decimal
                    from datetime import datetime
                    
                    quotes[symbol] = Quote(
                        instrument_id=InstrumentId(
                            figi=f"AV_{symbol}",
                            composite_ticker=symbol,
                            provider_symbol=symbol
                        ),
                        bid=Price(Decimal(quote_data.get("09. bid", 0)), 'USD', datetime.utcnow(), ProviderId.ALPHA_VANTAGE),
                        ask=Price(Decimal(quote_data.get("10. ask", 0)), 'USD', datetime.utcnow(), ProviderId.ALPHA_VANTAGE),
                        last=Price(Decimal(quote_data.get("05. price", 0)), 'USD', datetime.utcnow(), ProviderId.ALPHA_VANTAGE),
                        bid_size=None,
                        ask_size=None,
                        volume=int(quote_data.get("06. volume", 0)),
                        timestamp=datetime.utcnow(),
                        source=ProviderId.ALPHA_VANTAGE
                    )
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        return quotes

    async def get_history(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: DataFrequency = DataFrequency.DAY,
        adjustment: str = "none"
    ):
        try:
            function_map = {
                DataFrequency.MINUTE: "TIME_SERIES_INTRADAY",
                DataFrequency.HOUR: "TIME_SERIES_INTRADAY",
                DataFrequency.DAY: "TIME_SERIES_DAILY_ADJUSTED",
                DataFrequency.WEEK: "TIME_SERIES_WEEKLY_ADJUSTED",
                DataFrequency.MONTH: "TIME_SERIES_MONTHLY_ADJUSTED",
            }
            
            function = function_map.get(frequency, "TIME_SERIES_DAILY_ADJUSTED")
            interval_map = {
                DataFrequency.MINUTE: "1min",
                DataFrequency.HOUR: "60min",
            }
            interval = interval_map.get(frequency, "60min")
            
            params = {
                "function": function,
                "symbol": symbol,
                "apikey": self._api_key,
                "outputsize": "full",
                "datatype": "json"
            }
            if frequency in [DataFrequency.MINUTE, DataFrequency.HOUR]:
                params = {"function": "TIME_SERIES_INTRADAY", "symbol": symbol, "interval": interval, "apikey": self._api_key}
            
            data = await self._request({
                "function": function,
                "symbol": symbol,
                "interval": interval if frequency in [DataFrequency.MINUTE, DataFrequency.HOUR] else None,
                "apikey": self._api_key,
                "outputsize": "full",
                "datatype": "json"
            })
            
            # Parse response
            bars = []
            time_series_key = [k for k in data.keys() if "Time Series" in k]
            if time_series_key:
                ts_key = time_series_key[0]
                for timestamp, values in data[ts_key].items():
                    if hasattr(start, 'to_pydatetime'):
                        pass
                    bars.append(Bar(
                        instrument_id=InstrumentId(
                            figi=f"AV_{symbol}",
                            composite_ticker=symbol,
                            provider_symbol=symbol
                        ),
                        timestamp=datetime.fromisoformat(timestamp),
                        open=Decimal(values["1. open"]),
                        high=Decimal(values["2. high"]),
                        low=Decimal(values["3. low"]),
                        close=Decimal(values["4. close"]),
                        volume=int(values["5. volume"]),
                        frequency=DataFrequency.DAY,
                        source=ProviderId.ALPHA_VANTAGE,
                        adjustment="none"
                    ))
            return bars
        except Exception as e:
            logger.error(f"Alpha Vantage get_history failed: {e}")
            return []

    async def get_calendar(self, exchange: str, year: int):
        return {
            'exchange': exchange,
            'year': year,
            'trading_days': [],
            'holidays': [],
            'early_closes': []
        }

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return True

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.ALPHA_VANTAGE

    @property
    def name(self) -> str:
        return "Alpha Vantage"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY, AssetClass.FX, AssetClass.CRYPTO]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.MINUTE, DataFrequency.HOUR, DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 5, "burst": 1}

    async def health_check(self) -> bool:
        return True

    async def search_instruments(
        self,
        query: str,
        asset_class: Optional = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ):
        return []

    async def get_instrument(self, instrument_id):
        return None

    async def get_quotes(self, symbols, fields=None):
        return {}

    async def get_history(self, symbol, start, end, frequency=None, adjustment="none"):
        return []

    async def get_calendar(self, exchange: str, year: int):
        return {
            'exchange': exchange,
            'year': year,
            'trading_days': [],
            'holidays': [],
            'early_closes': []
        }

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return True

    async def get_quotes(self, symbols, fields=None):
        return {}

    async def get_history(self, symbol, start, end, frequency=None, adjustment="none"):
        return []

    async def get_calendar(self, exchange: str, year: int):
        return {
            'exchange': exchange,
            'year': year,
            'trading_days': [],
            'holidays': [],
            'early_closes': []
        }

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return True

    async def subscribe_quotes(self, symbols, callback):
        while True:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

    async def unsubscribe_quotes(self, symbols):
        pass

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return True

    async def get_quotes(self, symbols, fields=None):
        return {}

    async def get_history(self, symbol, start, end, frequency=None, adjustment="none"):
        return []

    async def get_calendar(self, exchange: str, year: int):
        return {
            'exchange': exchange,
            'year': year,
            'trading_days': [],
            'holidays': [],
            'early_closes': []
        }

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return True

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.ALPHA_VANTAGE

    @property
    def name(self) -> str:
        return "Alpha Vantage"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY, AssetClass.FX, AssetClass.CRYPTO]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.MINUTE, DataFrequency.HOUR, DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 5, "burst": 1}

    async def health_check(self) -> bool:
        return True