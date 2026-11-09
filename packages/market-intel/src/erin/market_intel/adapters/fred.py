"""FRED Provider Adapter - Federal Reserve Economic Data."""

import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator, TYPE_CHECKING
from decimal import Decimal

if TYPE_CHECKING:
    import fredapi

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


class FREDProvider:
    """FRED (Federal Reserve Economic Data) provider for macroeconomic indicators."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self._api_key = api_key
        self._timeout = timeout
        self._fred = None

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.FRED

    @property
    def name(self) -> str:
        return "FRED (Federal Reserve Economic Data)"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.FX, AssetClass.FIXED_INCOME, AssetClass.COMMODITY]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH, DataFrequency.QUARTER, DataFrequency.YEAR]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 120, "burst": 10}

    async def _get_fred(self):
        if self._fred is None:
            try:
                import fredapi
                self._fred = fredapi.Fred(api_key=self._api_key) if self._api_key else fredapi.Fred()
            except ImportError:
                logger.error("fredapi not installed")
                raise
        return self._fred

    async def health_check(self) -> bool:
        try:
            fred = await self._get_fred()
            # Test with a known series
            data = fred.get_series('GDP', limit=1)
            return data is not None and len(data) > 0
        except Exception as e:
            logger.warning(f"FRED health check failed: {e}")
            return False

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.FRED

    @property
    def name(self) -> str:
        return "FRED (Federal Reserve Economic Data)"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.FX, AssetClass.FIXED_INCOME, AssetClass.COMMODITY]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH, DataFrequency.QUARTER, DataFrequency.YEAR]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 120, "burst": 10}

    async def health_check(self) -> bool:
        try:
            fred = await self._get_fred()
            data = fred.get_series('GDP', limit=1)
            return data is not None and len(data) > 0
        except Exception as e:
            logger.warning(f"FRED health check failed: {e}")
            return False

    async def search_instruments(
        self,
        query: str,
        asset_class: Optional = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ):
        """Search FRED series."""
        try:
            fred = await self._get_fred()
            results = fred.search(query)
            instruments = []
            for _, row in results.head(limit).iterrows():
                series_id = row.get('id', '')
                if series_id:
                    from erin.market_intel.domain.interfaces import InstrumentId
                    instruments.append(InstrumentId(
                        figi=f"FRED_{series_id}",
                        composite_ticker=series_id,
                        provider_symbol=series_id
                    ))
            return instruments[:limit]
        except Exception as e:
            logger.error(f"FRED search failed: {e}")
            return []

    async def get_instrument(self, instrument_id):
        """Get FRED series metadata."""
        try:
            fred = await self._get_fred()
            series_id = instrument_id.composite_ticker
            info = fred.get_series_info(series_id)
            return info.to_dict() if hasattr(info, 'to_dict') else info
        except Exception as e:
            logger.error(f"FRED get_instrument failed: {e}")
            return None

    async def get_series(
        self,
        series_id: str,
        start: datetime = None,
        end: datetime = None
    ):
        """Get FRED time series data."""
        try:
            fred = await self._get_fred()
            data = fred.get_series(series_id, observation_start=start, observation_end=end)
            
            if data is not None and len(data) > 0:
                from erin.market_intel.domain.interfaces import Bar, InstrumentId, ProviderId, DataFrequency
                from decimal import Decimal
                
                bars = []
                for timestamp, value in data.items():
                    if pd.isna(value):
                        continue
                    bars.append(Bar(
                        instrument_id=self._to_instrument_id(series_id),
                        timestamp=timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp,
                        open=Decimal(str(value)),
                        high=Decimal(str(value)),
                        low=Decimal(str(value)),
                        close=Decimal(str(value)),
                        volume=0,
                        frequency=DataFrequency.DAY,
                        source=ProviderId.FRED,
                        adjustment="none"
                    ))
                return bars
            return []
        except Exception as e:
            logger.error(f"FRED get_series failed: {e}")
            return []

    async def get_series_info(self, series_id: str):
        """Get FRED series metadata."""
        try:
            fred = await self._get_fred()
            info = fred.get_series_info(series_id)
            return info.to_dict() if hasattr(info, 'to_dict') else info
        except Exception as e:
            logger.error(f"FRED get_series_info failed: {e}")
            return None

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
        return True  # FRED API key recommended for higher limits

    def _to_instrument_id(self, series_id: str):
        from erin.market_intel.domain.interfaces import InstrumentId
        return InstrumentId(
            figi=f"FRED_{series_id}",
            composite_ticker=series_id,
            provider_symbol=series_id
        )

    async def health_check(self) -> bool:
        try:
            fred = await self._get_fred()
            data = fred.get_series('GDP', limit=1)
            return data is not None and len(data) > 0
        except Exception as e:
            logger.warning(f"FRED health check failed: {e}")
            return False

    async def search_instruments(
        self,
        query: str,
        asset_class=None,
        exchange=None,
        limit: int = 50
    ):
        try:
            fred = await self._get_fred()
            results = fred.search(query)
            instruments = []
            for _, row in results.head(limit).iterrows():
                series_id = row.get('id', '')
                if series_id:
                    from erin.market_intel.domain.interfaces import InstrumentId
                    instruments.append(InstrumentId(
                        figi=f"FRED_{series_id}",
                        composite_ticker=series_id,
                        provider_symbol=series_id
                    ))
            return instruments[:limit]
        except Exception as e:
            logger.error(f"FRED search failed: {e}")
            return []

    async def get_instrument(self, instrument_id):
        try:
            fred = await self._get_fred()
            series_id = instrument_id.composite_ticker
            info = fred.get_series_info(series_id)
            return info.to_dict() if hasattr(info, 'to_dict') else info
        except Exception as e:
            logger.error(f"FRED get_instrument failed: {e}")
            return None

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
        return ProviderId.FRED

    @property
    def name(self) -> str:
        return "FRED (Federal Reserve Economic Data)"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.FX, AssetClass.FIXED_INCOME, AssetClass.COMMODITY]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH, DataFrequency.QUARTER, DataFrequency.YEAR]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 120, "burst": 10}

    async def health_check(self) -> bool:
        try:
            fred = await self._get_fred()
            data = fred.get_series('GDP', limit=1)
            return data is not None and len(data) > 0
        except Exception as e:
            logger.warning(f"FRED health check failed: {e}")
            return False

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
        return ProviderId.FRED

    @property
    def name(self) -> str:
        return "FRED (Federal Reserve Economic Data)"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.FX, AssetClass.FIXED_INCOME, AssetClass.COMMODITY]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return [DataFrequency.DAY, DataFrequency.WEEK, DataFrequency.MONTH, DataFrequency.QUARTER, DataFrequency.YEAR]

    @property
    def rate_limit(self):
        return {"requests_per_minute": 120, "burst": 10}

    async def health_check(self) -> bool:
        try:
            fred = await self._get_fred()
            data = fred.get_series('GDP', limit=1)
            return data is not None and len(data) > 0
        except Exception as e:
            logger.warning(f"FRED health check failed: {e}")
            return False

    async def search_instruments(
        self,
        query: str,
        asset_class=None,
        exchange=None,
        limit: int = 50
    ):
        try:
            fred = await self._get_fred()
            results = fred.search(query)
            instruments = []
            for _, row in results.head(limit).iterrows():
                series_id = row.get('id', '')
                if series_id:
                    from erin.market_intel.domain.interfaces import InstrumentId
                    instruments.append(InstrumentId(
                        figi=f"FRED_{series_id}",
                        composite_ticker=series_id,
                        provider_symbol=series_id
                    ))
            return instruments[:limit]
        except Exception as e:
            logger.error(f"FRED search failed: {e}")
            return []

    async def get_instrument(self, instrument_id):
        try:
            fred = await self._get_fred()
            series_id = instrument_id.composite_ticker
            info = fred.get_series_info(series_id)
            return info.to_dict() if hasattr(info, 'to_dict') else info
        except Exception as e:
            logger.error(f"FRED get_instrument failed: {e}")
            return None

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