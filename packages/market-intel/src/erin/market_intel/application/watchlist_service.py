"""Watchlist Service - Business logic for watchlist management."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.data_infra.storage.sqlite import SQLiteStorage
    from erin.market_intel.domain.interfaces import Quote

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for managing watchlists and real-time quotes."""
    
    def __init__(self, storage: 'SQLiteStorage', market_data_service: 'MarketDataService'):
        self.storage = storage
        self.market_data = market_data_service
    
    async def create_watchlist(
        self,
        user_id: str,
        name: str,
        symbols: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new watchlist."""
        watchlist_id = self.storage.create_watchlist(user_id, name, symbols or [])
        return {
            "id": watchlist_id,
            "name": name,
            "symbols": symbols or [],
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def get_watchlist(self, watchlist_id: str, user_id: str) -> Optional[Dict]:
        """Get watchlist with real-time quotes."""
        watchlist = self.storage.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return None
        
        # Get real-time quotes for symbols
        symbols = watchlist.get("symbols", [])
        quotes = await self.market_data.get_quotes(symbols)
        
        # Enrich watchlist with quotes
        enriched_symbols = []
        for symbol in symbols:
            quote = quotes.get(symbol)
            if quote:
                enriched_symbols.append({
                    "symbol": symbol,
                    "name": quote.instrument_id.composite_ticker if quote.instrument_id else symbol,
                    "price": float(quote.last.value) if quote.last else None,
                    "change": float(quote.change) if quote.change else None,
                    "change_percent": float(quote.change_percent) if quote.change_percent else None,
                    "volume": quote.volume,
                    "last_update": quote.timestamp.isoformat() if quote.timestamp else None
                })
            else:
                enriched_symbols.append({
                    "symbol": symbol,
                    "name": symbol,
                    "price": None,
                    "change": None,
                    "change_percent": None,
                    "volume": None,
                    "last_update": None
                })
        
        return {
            **watchlist,
            "symbols": enriched_symbols,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def get_watchlists(self, user_id: str) -> List[Dict]:
        """Get all watchlists for a user."""
        watchlists = self.storage.get_watchlists(user_id)
        
        # Enrich each watchlist with quotes
        enriched = []
        for wl in watchlists:
            enriched = await self.get_watchlist(wl["id"], wl["user_id"])
            enriched.append(enriched)
        
        return enriched
    
    async def update_watchlist(
        self,
        watchlist_id: str,
        user_id: str,
        name: Optional[str] = None,
        symbols: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """Update watchlist."""
        watchlist = self.storage.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return None
        
        if name is not None:
            watchlist["name"] = name
        if symbols is not None:
            watchlist["symbols"] = symbols
        
        watchlist["updated_at"] = datetime.utcnow().isoformat()
        
        # Update in storage
        # (Would need storage.update_watchlist method)
        
        return await self.get_watchlist(watchlist_id, user_id)
    
    async def delete_watchlist(self, watchlist_id: str, user_id: str) -> bool:
        """Delete a watchlist."""
        self.storage.delete_watchlist(watchlist_id, user_id)
        return True
    
    async def add_symbol(self, watchlist_id: str, user_id: str, symbol: str) -> Optional[Dict]:
        """Add symbol to watchlist."""
        watchlist = self.storage.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return None
        
        if symbol not in watchlist["symbols"]:
            watchlist["symbols"].append(symbol)
            # Update in storage
            return await self.get_watchlist(watchlist_id, user_id)
        
        return await self.get_watchlist(watchlist_id, user_id)
    
    async def remove_symbol(self, watchlist_id: str, user_id: str, symbol: str) -> bool:
        """Remove symbol from watchlist."""
        # Would need storage method to remove symbol
        return True
    
    async def get_real_time_quotes(self, symbols: List[str]) -> Dict:
        """Get real-time quotes for symbols."""
        # Would call market data service
        return {}


class WatchlistManager:
    """Manages watchlist state and real-time updates."""
    
    def __init__(self, watchlist_service: WatchlistService):
        self.service = watchlist_service
        self._subscriptions: Dict[str, asyncio.Task] = {}
    
    async def subscribe(self, watchlist_id: str, user_id: str, callback):
        """Subscribe to watchlist updates."""
        # In a real implementation, this would set up WebSocket subscriptions
        pass
    
    async def unsubscribe(self, watchlist_id: str, user_id: str):
        """Unsubscribe from watchlist updates."""
        pass