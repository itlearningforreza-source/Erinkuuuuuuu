"""Portfolio Service - Portfolio management, analytics, and risk analytics."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from erin.data_infra.storage.sqlite import SQLiteStorage
    from erin.market_intel.domain.interfaces import Quote, CurrencyCode

logger = logging.getLogger(__name__)


class TransactionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Position:
    """Portfolio position."""
    figi: str
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    currency: str
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    opened_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def update_price(self, price: Decimal):
        self.current_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = (price - self.avg_cost) * self.quantity
        if self.avg_cost > 0:
            self.unrealized_pnl_pct = (price - self.avg_cost) / self.avg_cost
        else:
            self.unrealized_pnl_pct = Decimal('0')
        self.last_updated = datetime.utcnow()
    
    @property
    def weight_pct(self) -> Decimal:
        """Position weight as percentage."""
        if self.weight:
            return self.weight * Decimal('100')
        return Decimal('0')


@dataclass
class CashBalance:
    """Cash balance in a currency."""
    currency: str
    amount: Decimal
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Portfolio:
    """Portfolio with positions and cash."""
    id: str
    user_id: str
    name: str
    base_currency: str
    positions: Dict[str, 'Position'] = field(default_factory=dict)
    cash_balances: Dict[str, CashBalance] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_total_value(self, quotes: Dict[str, 'Quote'] = None) -> Decimal:
        """Calculate total portfolio value."""
        total = Decimal('0')
        
        # Add positions
        for pos in self.positions.values():
            if quotes and pos.figi in quotes:
                quote = quotes[pos.figi]
                if quote.last:
                    pos.update_price(quote.last.value)
            
            if pos.market_value:
                total += pos.market_value
        
        # Add cash
        for cash in self.cash_balances.values():
            total += cash.amount
        
        return total
    
    def get_weights(self, quotes: Dict[str, 'Quote'] = None) -> Dict[str, Decimal]:
        """Get position weights."""
        total = self.get_total_value(quotes)
        weights = {}
        
        if total == 0:
            return weights
        
        for figi, pos in self.positions.items():
            if pos.market_value:
                weights[pos.figi] = pos.market_value / total
        
        for currency, cash in self.cash_balances.items():
            if cash.amount:
                weights[f"CASH_{currency}"] = cash.amount / total
        
        return weights
    
    def get_position(self, figi: str) -> Optional['Position']:
        return self.positions.get(figi)


@dataclass
class Transaction:
    """Portfolio transaction."""
    id: str
    portfolio_id: str
    figi: str
    side: TransactionSide
    quantity: Decimal
    price: Decimal
    price_currency: str
    fees: Decimal = Decimal('0')
    fees_currency: str = 'USD'
    slippage: Optional[Decimal] = None
    slippage_currency: Optional[str] = None
    executed_at: datetime
    status: str = 'FILLED'  # FILLED, PARTIAL, CANCELLED, REJECTED
    broker: Optional[str] = None
    order_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class PortfolioService:
    """Portfolio management service."""
    
    def __init__(self, storage, market_data_service):
        self.storage = storage
        self.market_data = market_data_service
    
    async def create_portfolio(
        self,
        user_id: str,
        name: str,
        base_currency: str = 'USD'
    ) -> Dict:
        """Create a new portfolio."""
        portfolio_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name=name,
            base_currency=base_currency
        )
        
        # Save to storage (would need storage method)
        # For now, return the portfolio object
        return {
            "id": portfolio.id,
            "user_id": user_id,
            "name": name,
            "base_currency": base_currency,
            "positions": {},
            "cash_balances": {base_currency: 0},
            "total_value": 0,
            "created_at": now.isoformat()
        }
    
    async def get_portfolio(self, portfolio_id: str, user_id: str) -> Optional[Dict]:
        """Get portfolio with current positions and values."""
        # Would fetch from storage
        # For now, return mock
        return {
            "id": "mock",
            "user_id": user_id,
            "name": "Demo Portfolio",
            "base_currency": "USD",
            "positions": {},
            "cash_balances": {"USD": 100000},
            "total_value": 100000,
            "cash": 100000,
            "positions_value": 0
        }
    
    async def add_position(
        self,
        portfolio_id: str,
        user_id: str,
        figi: str,
        quantity: Decimal,
        avg_cost: Decimal,
        currency: str = 'USD'
    ) -> Dict:
        """Add or update position."""
        # In real implementation, would update storage
        return {
            "figi": figi,
            "quantity": float(quantity),
            "avg_cost": float(avg_cost),
            "currency": currency
        }
    
    async def remove_position(self, portfolio_id: str, figi: str) -> bool:
        """Remove position from portfolio."""
        return True
    
    async def add_transaction(
        self,
        portfolio_id: str,
        user_id: str,
        figi: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal = Decimal('0'),
        executed_at: datetime = None,
        broker: Optional[str] = None
    ) -> Dict:
        """Record a transaction."""
        transaction_id = str(uuid.uuid4())
        executed_at = executed_at or datetime.utcnow()
        
        transaction = {
            "id": str(uuid.uuid4()),
            "portfolio_id": portfolio_id,
            "figi": figi,
            "side": side,
            "quantity": float(quantity),
            "price": float(price),
            "fees": float(fees),
            "executed_at": executed_at.isoformat(),
            "status": "FILLED",
            "broker": broker
        }
        
        # Update position based on transaction
        # In real implementation, would update position
        
        return transaction
    
    async def get_portfolio_metrics(
        self,
        portfolio_id: str,
        user_id: str,
        quotes: Dict = None
    ) -> Dict:
        """Calculate portfolio metrics."""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        
        if not portfolio:
            return {}
        
        total_value = portfolio.get("total_value", 0)
        cash = portfolio.get("cash", 0)
        positions_value = portfolio.get("positions_value", 0)
        
        # Calculate metrics
        pnl = positions_value - sum(
            pos.get("quantity", 0) * pos.get("avg_cost", 0) 
            for pos in portfolio.get("positions", {}).values()
        )
        
        pnl_pct = (pnl / (cash + positions_value) * 100) if (cash + positions_value) > 0 else 0
        
        # Concentration (HHI)
        weights = []
        for pos in portfolio.get("positions", {}).values():
            if pos.get("market_value"):
                weights.append(pos["market_value"])
        
        total_pos = sum(weights)
        hhi = sum((w/total_pos)**2 for w in weights) if total_pos > 0 else 0
        
        return {
            "total_value": total_value,
            "cash": cash,
            "positions_value": positions_value,
            "pnl": float(pnl),
            "pnl_pct": float(pnl_pct),
            "concentration_hhi": float(hhi),
            "num_positions": len(portfolio.get("positions", {})),
            "largest_position_pct": max(
                [w/total_pos for w in weights], default=0
            ) if total_pos > 0 else 0
        }
    
    async def rebalance(
        self,
        portfolio_id: str,
        target_weights: Dict[str, Decimal],
        user_id: str
    ) -> List[Dict]:
        """Generate rebalance orders."""
        # Would generate orders to rebalance to target weights
        orders = []
        
        # In real implementation:
        # 1. Get current portfolio and prices
        # 2. Calculate target positions
        # 3. Generate buy/sell orders
        # 4. Return order list
        
        return orders