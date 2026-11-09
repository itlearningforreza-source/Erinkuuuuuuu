"""Instrument Master - Canonical instrument registry with FIGI-based identity."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    pass

from erin.market_intel.domain.interfaces import (
    InstrumentId,
    AssetClass,
    CurrencyCode,
    ProviderId,
)

logger = logging.getLogger(__name__)


class InstrumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DELISTED = "DELISTED"
    SUSPENDED = "SUSPENDED"
    MERGED = "MERGED"
    INACTIVE = "INACTIVE"


@dataclass
class Instrument:
    """Canonical instrument record with full metadata."""
    
    # Identity (immutable)
    figi: str                          # OpenFIGI - globally unique
    composite_ticker: str              # e.g., "AAPL.US", "7203.T"
    
    # Core metadata (required fields first)
    name: str                          # Full company/security name
    asset_class: AssetClass
    primary_exchange: str              # Primary listing exchange (MIC code)
    currency: str                      # ISO 4217 currency code
    country: str                       # ISO 3166-1 alpha-2 country code
    
    # Provider mappings (symbol -> provider)
    provider_symbols: Dict[str, str] = field(default_factory=dict)  # provider -> symbol
    
    # Classification
    sector: Optional[str] = None
    industry: Optional[str] = None
    gics_code: Optional[str] = None
    sic_code: Optional[str] = None
    
    # Status & lifecycle
    status: InstrumentStatus = InstrumentStatus.ACTIVE
    ipo_date: Optional[datetime] = None
    delisted_date: Optional[datetime] = None
    
    # Trading parameters
    lot_size: int = 1                  # Minimum trade quantity
    tick_size: Decimal = Decimal("0.01")  # Minimum price increment
    currency_decimals: int = 2
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    
    # Provider-specific symbols (alias mappings)
    # e.g., {"openbb": "AAPL", "yfinance": "AAPL", "alpha_vantage": "AAPL", "fred": "FRED_AAPL"}
    
    def __post_init__(self):
        # Ensure composite_ticker is uppercase
        self.composite_ticker = self.composite_ticker.upper()
        
    @property
    def primary_symbol(self) -> str:
        """Primary display symbol (composite_ticker)."""
        return self.composite_ticker
    
    def get_provider_symbol(self, provider: str) -> Optional[str]:
        """Get provider-specific symbol."""
        return self.provider_symbols.get(provider.lower())
    
    def set_provider_symbol(self, provider: str, symbol: str) -> None:
        """Set provider-specific symbol."""
        self.provider_symbols[provider.lower()] = symbol
        self.updated_at = datetime.utcnow()
        self.version += 1

    def get_figi(self) -> str:
        """Get FIGI identifier."""
        return self.figi


class InstrumentMaster:
    """Central registry for all instruments with FIGI-based identity."""
    
    def __init__(self):
        self._instruments: Dict[str, Instrument] = {}  # figi -> Instrument
        self._ticker_index: Dict[str, str] = {}  # composite_ticker -> figi
        self._provider_symbol_index: Dict[str, Dict[str, str]] = {}  # provider -> symbol -> figi
        self._figi_counter = 0
    
    def create_instrument(
        self,
        composite_ticker: str,
        name: str,
        asset_class: str,
        primary_exchange: str,
        currency: str,
        country: str,
        figi: Optional[str] = None,
        **kwargs
    ) -> Instrument:
        """Create a new instrument."""
        composite_ticker = composite_ticker.upper()
        
        # Check if already exists by ticker
        if composite_ticker in self._ticker_index:
            figi = self._ticker_index[composite_ticker]
            existing = self._instruments[figi]
            # Update existing
            for k, v in kwargs.items():
                if hasattr(existing, k) and v is not None:
                    setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            existing.version += 1
            return existing
        
        # Generate FIGI if not provided
        if figi is None:
            self._figi_counter += 1
            figi = f"FIGI_{self._figi_counter:08d}"
        
        # Create instrument
        instrument = Instrument(
            figi=figi,
            composite_ticker=composite_ticker,
            name=name,
            asset_class=asset_class,
            primary_exchange=primary_exchange,
            currency=currency,
            country=country,
            **kwargs
        )
        
        # Index
        self._instruments[figi] = instrument
        self._ticker_index[composite_ticker] = figi
        
        return instrument
    
    def get_by_figi(self, figi: str) -> Optional[Instrument]:
        """Get instrument by FIGI."""
        return self._instruments.get(figi)
    
    def get_by_ticker(self, composite_ticker: str) -> Optional[Instrument]:
        """Get instrument by composite ticker."""
        figi = self._ticker_index.get(composite_ticker.upper())
        if figi:
            return self._instruments.get(figi)
        return None
    
    def get_by_provider_symbol(self, provider: str, symbol: str) -> Optional[Instrument]:
        """Get instrument by provider-specific symbol."""
        provider = provider.lower()
        figi = self._provider_symbol_index.get(provider, {}).get(symbol)
        if figi:
            return self._instruments.get(figi)
        return None
    
    def register_provider_symbol(self, figi: str, provider: str, symbol: str) -> bool:
        """Register a provider-specific symbol for an instrument."""
        instrument = self._instruments.get(figi)
        if not instrument:
            return False
        
        provider = provider.lower()
        instrument.set_provider_symbol(provider, symbol)
        
        # Update index
        if provider not in self._provider_symbol_index:
            self._provider_symbol_index[provider] = {}
        self._provider_symbol_index[provider][symbol] = figi
        
        return True
    
    def search(self, query: str, limit: int = 50) -> List[Instrument]:
        """Search instruments by ticker or name."""
        query = query.upper()
        results = []
        
        # Exact ticker match first
        if query in self._ticker_index:
            figi = self._ticker_index[query]
            if figi in self._instruments:
                return [self._instruments[figi]]
        
        # Partial ticker match
        for ticker, figi in self._ticker_index.items():
            if query in ticker:
                results.append(self._instruments[figi])
                if len(results) >= limit:
                    break
        
        # Name search
        if len(results) < limit:
            for instrument in self._instruments.values():
                if query in instrument.name.upper():
                    results.append(instrument)
                    if len(results) >= limit:
                        break
        
        return results[:limit]
    
    def get_all(self, limit: int = 1000, offset: int = 0) -> List[Instrument]:
        """Get all instruments with pagination."""
        instruments = list(self._instruments.values())
        return instruments[offset:offset + limit]
    
    def count(self) -> int:
        return len(self._instruments)
    
    def update_instrument(self, figi: str, updates: Dict[str, Any]) -> bool:
        """Update instrument fields."""
        instrument = self._instruments.get(figi)
        if not instrument:
            return False
        
        for key, value in updates.items():
            if hasattr(instrument, key):
                setattr(instrument, key, value)
        
        instrument.updated_at = datetime.utcnow()
        instrument.version += 1
        return True
    
    def deactivate(self, figi: str, reason: str = "") -> bool:
        """Mark instrument as delisted/inactive."""
        instrument = self._instruments.get(figi)
        if not instrument:
            return False
        
        instrument.status = InstrumentStatus.DELISTED
        instrument.delisted_date = datetime.utcnow()
        instrument.metadata["delist_reason"] = reason
        instrument.updated_at = datetime.utcnow()
        instrument.version += 1
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get master statistics."""
        status_counts = {}
        asset_class_counts = {}
        
        for instrument in self._instruments.values():
            status_counts[instrument.status.value] = status_counts.get(instrument.status.value, 0) + 1
            
            # Handle both enum and string asset_class
            if hasattr(instrument.asset_class, 'value'):
                ac_value = instrument.asset_class.value
            else:
                ac_value = str(instrument.asset_class)
            asset_class_counts[ac_value] = asset_class_counts.get(ac_value, 0) + 1
        
        return {
            "total_instruments": len(self._instruments),
            "by_status": status_counts,
            "by_asset_class": asset_class_counts,
            "provider_mappings": {
                provider: len(symbols) 
                for provider, symbols in self._provider_symbol_index.items()
            }
        }


# Global instance
instrument_master = InstrumentMaster()


# Pre-populate with common instruments
def seed_common_instruments():
    """Seed instrument master with common instruments."""
    
    common_stocks = [
        {
            "composite_ticker": "AAPL.US",
            "name": "Apple Inc.",
            "asset_class": "EQUITY",
            "primary_exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "gics_code": "45201010",
        },
        {
            "composite_ticker": "MSFT.US",
            "name": "Microsoft Corporation",
            "asset_class": "EQUITY",
            "primary_exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Technology",
            "industry": "Software",
            "gics_code": "45101010",
        },
        {
            "composite_ticker": "GOOGL.US",
            "name": "Alphabet Inc. Class A",
            "asset_class": "EQUITY",
            "primary_exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Communication Services",
            "industry": "Interactive Media & Services",
            "gics_code": "50201010",
        },
        {
            "composite_ticker": "AMZN.US",
            "name": "Amazon.com Inc.",
            "asset_class": "EQUITY",
            "primary_exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Consumer Discretionary",
            "industry": "Internet & Direct Marketing Retail",
            "gics_code": "25501010",
        },
        {
            "composite_ticker": "TSLA.US",
            "name": "Tesla Inc.",
            "asset_class": "EQUITY",
            "primary_exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Consumer Discretionary",
            "industry": "Automobiles",
            "gics_code": "25101010",
        },
        {
            "composite_ticker": "NVDA.US",
            "name": "NVIDIA Corporation",
            "asset_class": "EQUITY",
            "primary_exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Technology",
            "industry": "Semiconductors",
            "gics_code": "45301010",
        },
        {
            "composite_ticker": "JPM.US",
            "name": "JPMorgan Chase & Co.",
            "asset_class": "EQUITY",
            "primary_exchange": "NYSE",
            "currency": "USD",
            "country": "US",
            "sector": "Financials",
            "industry": "Diversified Banks",
            "gics_code": "40101010",
        },
        {
            "composite_ticker": "V.US",
            "name": "Visa Inc. Class A",
            "asset_class": "EQUITY",
            "primary_exchange": "NYSE",
            "currency": "USD",
            "country": "US",
            "sector": "Information Technology",
            "industry": "Transaction & Payment Processing",
            "gics_code": "45102010",
        },
    ]
    
    for stock in common_stocks:
        instrument_master.create_instrument(**stock)
        # Register provider symbols
        ticker = stock["composite_ticker"]
        figi = instrument_master._ticker_index[ticker]
        instrument_master.register_provider_symbol(figi, "openbb", ticker)
        instrument_master.register_provider_symbol(figi, "yfinance", ticker)
        instrument_master.register_provider_symbol(figi, "alpha_vantage", ticker)
        instrument_master.register_provider_symbol(figi, "fred", f"FRED_{ticker}")

# Initialize on import
seed_common_instruments()