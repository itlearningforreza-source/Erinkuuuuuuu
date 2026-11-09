"""yfinance Provider Adapter - Free fallback for equity data."""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator
import yfinance as yf
import pandas as pd

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


class YFinanceProvider:
    """yfinance market data provider adapter (free, no API key required)."""

    def __init__(self, timeout: int = 30):
        self._timeout = timeout
        self._cache: Dict[str, Any] = {}

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.YFINANCE

    @property
    def name(self) -> str:
        return "Yahoo Finance"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY, AssetClass.FUND, AssetClass.CRYPTO, AssetClass.FX]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [
            DataFrequency.MINUTE,
            DataFrequency.HOUR,
            DataFrequency.DAY,
            DataFrequency.WEEK,
            DataFrequency.MONTH,
        ]

    @property
    def rate_limit(self) -> Dict[str, int]:
        return {"requests_per_minute": 30, "burst": 5}

    async def health_check(self) -> bool:
        try:
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            return info is not None and 'symbol' in info
        except Exception as e:
            logger.warning(f"yfinance health check failed: {e}")
            return False

    def _to_instrument_id(self, symbol: str):
        from erin.market_intel.domain.interfaces import InstrumentId
        return InstrumentId(
            figi=f"FIGI_{symbol}",
            composite_ticker=symbol,
            provider_symbol=symbol
        )

    def _to_quote(self, symbol: str, info: Dict) -> 'Quote':
        from erin.market_intel.domain.interfaces import Quote, Price, InstrumentId, ProviderId
        from decimal import Decimal
        from datetime import datetime
        
        instrument_id = self._to_instrument_id(symbol)
        now = datetime.utcnow()
        
        return Quote(
            instrument_id=self._to_instrument_id(symbol),
            bid=Price(Decimal(str(info.get('bid', 0))), 'USD', datetime.utcnow(), ProviderId.YFINANCE) if info.get('bid') else None,
            ask=Price(Decimal(str(info.get('ask', 0))), 'USD', datetime.utcnow(), ProviderId.YFINANCE) if info.get('ask') else None,
            last=Price(Decimal(str(info.get('currentPrice', info.get('regularMarketPrice', 0)))), 'USD', datetime.utcnow(), ProviderId.YFINANCE),
            bid_size=info.get('bidSize'),
            ask_size=info.get('askSize'),
            volume=info.get('volume', info.get('regularMarketVolume')),
            timestamp=datetime.utcnow(),
            source=ProviderId.YFINANCE
        )

    def _to_bar(self, symbol: str, row: Any, freq):
        from erin.market_intel.domain.interfaces import Bar, InstrumentId, ProviderId, DataFrequency
        from decimal import Decimal
        import pandas as pd
        
        instrument_id = self._to_instrument_id(symbol)
        
        if hasattr(row, 'to_dict'):
            data = row.to_dict()
        elif isinstance(row, dict):
            data = row
        else:
            data = dict(row)
        
        date_val = data.get('Date', data.get('date', datetime.utcnow()))
        if isinstance(date_val, str):
            timestamp = pd.Timestamp(date_val).to_pydatetime()
        else:
            timestamp = pd.Timestamp(date_val).to_pydatetime() if hasattr(date_val, 'to_pydatetime') else datetime.utcnow()
        
        return Bar(
            instrument_id=self._to_instrument_id(symbol),
            timestamp=timestamp,
            open=Decimal(str(data.get('Open', data.get('open', 0)))),
            high=Decimal(str(data.get('High', data.get('high', 0)))),
            low=Decimal(str(data.get('Low', data.get('low', 0)))),
            close=Decimal(str(data.get('Close', data.get('close', 0)))),
            volume=int(data.get('Volume', data.get('volume', 0))),
            frequency=DataFrequency.DAY,
            source=ProviderId.YFINANCE,
            adjustment="none"
        )

    async def health_check(self) -> bool:
        try:
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            return info is not None and 'symbol' in info
        except Exception as e:
            logger.warning(f"yfinance health check failed: {e}")
            return False

    async def search_instruments(
        self,
        query: str,
        asset_class: Optional = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ):
        """Search instruments - yfinance doesn't have search, return basic match."""
        # yfinance doesn't have search, return basic match if valid
        try:
            ticker = yf.Ticker(query.upper())
            info = ticker.info
            if info and 'symbol' in info:
                from erin.market_intel.domain.interfaces import InstrumentId
                return [InstrumentId(
                    figi=f"FIGI_{query.upper()}",
                    composite_ticker=query.upper(),
                    provider_symbol=query.upper()
                )]
        except Exception:
            pass
        return []

    async def get_instrument(self, instrument_id):
        try:
            ticker = yf.Ticker(instrument_id.composite_ticker)
            info = ticker.info
            return info if info else None
        except Exception as e:
            logger.error(f"yfinance get_instrument failed: {e}")
            return None

    async def get_quotes(self, symbols: List[str], fields: Optional[List[str]] = None):
        quotes = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if info:
                    from erin.market_intel.domain.interfaces import Quote, Price, InstrumentId, ProviderId
                    from decimal import Decimal
                    from datetime import datetime
                    
                    instrument_id = self._to_instrument_id(symbol)
                    now = datetime.utcnow()
                    
                    quotes[symbol] = Quote(
                        instrument_id=self._to_instrument_id(symbol),
                        bid=Price(Decimal(str(info.get('bid', 0))), 'USD', datetime.utcnow(), ProviderId.YFINANCE) if info.get('bid') else None,
                        ask=Price(Decimal(str(info.get('ask', 0))), 'USD', datetime.utcnow(), ProviderId.YFINANCE) if info.get('ask') else None,
                        last=Price(Decimal(str(info.get('currentPrice', info.get('regularMarketPrice', 0)))), 'USD', datetime.utcnow(), ProviderId.YFINANCE),
                        bid_size=info.get('bidSize'),
                        ask_size=info.get('askSize'),
                        volume=info.get('volume', info.get('regularMarketVolume')),
                        timestamp=datetime.utcnow(),
                        source=ProviderId.YFINANCE
                    )
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        return quotes

    async def get_history(self, symbol: str, start, end, frequency=DataFrequency.DAY, adjustment="none"):
        try:
            ticker = yf.Ticker(symbol)
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '1d': '1d', '1wk': '1wk', '1mo': '1mo'
            }
            interval = '1d'  # Default
            data = ticker.history(start=start, end=end, interval='1d')
            
            bars = []
            if data is not None and len(data) > 0:
                for _, row in data.iterrows():
                    bars.append(self._to_bar(symbol, row, frequency))
            return bars
        except Exception as e:
            logger.error(f"yfinance get_history failed: {e}")
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
        return False

    async def subscribe_quotes(self, symbols: List[str], callback):
        # Polling fallback
        interval = 5
        while True:
            try:
                quotes = await self.get_quotes(symbols)
                for symbol, quote in quotes.items():
                    await callback(quote)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Quote polling error: {e}")
                await asyncio.sleep(5)

    async def unsubscribe_quotes(self, symbols: List[str]):
        pass

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return False

    def _map_frequency(self, freq):
        mapping = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '1d': '1d', '1wk': '1wk', '1mo': '1mo'
        }
        return mapping.get(freq.value if hasattr(freq, 'value') else str(freq), '1d')

    def _to_instrument_id(self, symbol: str):
        from erin.market_intel.domain.interfaces import InstrumentId
        return InstrumentId(
            figi=f"FIGI_{symbol}",
            composite_ticker=symbol,
            provider_symbol=symbol
        )

    def _to_bar(self, symbol: str, row: Any, freq):
        from erin.market_intel.domain.interfaces import Bar, InstrumentId, ProviderId, DataFrequency
        from decimal import Decimal
        import pandas as pd
        
        instrument_id = self._to_instrument_id(symbol)
        
        if hasattr(row, 'to_dict'):
            data = row.to_dict()
        elif isinstance(row, dict):
            data = row
        else:
            data = dict(row)
        
        date_val = data.get('Date', data.get('date', datetime.utcnow()))
        if isinstance(date_val, str):
            timestamp = pd.Timestamp(date_val).to_pydatetime()
        else:
            timestamp = pd.Timestamp(date_val).to_pydatetime() if hasattr(date_val, 'to_pydatetime') else datetime.utcnow()
        
        return Bar(
            instrument_id=self._to_instrument_id(symbol),
            timestamp=timestamp,
            open=Decimal(str(data.get('Open', data.get('open', 0)))),
            high=Decimal(str(data.get('High', data.get('high', 0)))),
            low=Decimal(str(data.get('Low', data.get('low', 0)))),
            close=Decimal(str(data.get('Close', data.get('close', 0)))),
            volume=int(data.get('Volume', data.get('volume', 0))),
            frequency=DataFrequency.DAY,
            source=ProviderId.YFINANCE,
            adjustment="none"
        )

    def _to_quote(self, symbol: str, info: Dict) -> 'Quote':
        from erin.market_intel.domain.interfaces import Quote, Price, InstrumentId, ProviderId
        from decimal import Decimal
        from datetime import datetime
        
        instrument_id = self._to_instrument_id(symbol)
        now = datetime.utcnow()
        
        return Quote(
            instrument_id=self._to_instrument_id(symbol),
            bid=Price(Decimal(str(info.get('bid', 0))), 'USD', datetime.utcnow(), ProviderId.YFINANCE) if info.get('bid') else None,
            ask=Price(Decimal(str(info.get('ask', 0))), 'USD', datetime.utcnow(), ProviderId.YFINANCE) if info.get('ask') else None,
            last=Price(Decimal(str(info.get('currentPrice', info.get('regularMarketPrice', 0)))), 'USD', datetime.utcnow(), ProviderId.YFINANCE),
            bid_size=info.get('bidSize'),
            ask_size=info.get('askSize'),
            volume=info.get('volume', info.get('regularMarketVolume')),
            timestamp=datetime.utcnow(),
            source=ProviderId.YFINANCE
        )