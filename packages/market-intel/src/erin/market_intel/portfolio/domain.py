"""Portfolio Domain - Core portfolio, position, and transaction models."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.market_intel.domain.interfaces import Quote


class TransactionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"          # Good Till Cancelled
    IOC = "IOC"          # Immediate or Cancel
    FOK = "FOK"          # Fill or Kill
    GTD = "GTD"          # Good Till Date


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Portfolio position with P&L tracking."""
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str = ""
    figi: str = ""
    symbol: str = ""
    
    # Position details
    side: PositionSide = PositionSide.LONG
    quantity: Decimal = Decimal('0')
    avg_cost: Decimal = Decimal('0')
    currency: str = "USD"
    
    # Market data
    current_price: Optional[Decimal] = None
    current_price_date: Optional[datetime] = None
    
    # P&L
    unrealized_pnl: Decimal = Decimal('0')
    unrealized_pnl_pct: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    
    # Risk metrics
    beta: Optional[Decimal] = None
    var_contribution: Optional[Decimal] = None
    
    # Metadata
    opened_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def market_value(self) -> Decimal:
        if self.current_price and self.quantity:
            return self.current_price * self.quantity
        return Decimal('0')
    
    @property
    def cost_basis(self) -> Decimal:
        return self.avg_cost * self.quantity
    
    def update_price(self, price: Decimal, timestamp: datetime = None):
        """Update current price and recalculate P&L."""
        self.current_price = price
        self.current_price_date = timestamp or datetime.utcnow()
        
        if self.quantity != 0 and self.avg_cost != 0:
            self.unrealized_pnl = (price - self.avg_cost) * self.quantity
            self.unrealized_pnl_pct = (price - self.avg_cost) / self.avg_cost
        else:
            self.unrealized_pnl = Decimal('0')
            self.unrealized_pnl_pct = Decimal('0')
        
        self.last_updated = datetime.utcnow()
    
    def add_quantity(self, qty: Decimal, price: Decimal, side: TransactionSide):
        """Add to position with cost averaging."""
        if side == TransactionSide.BUY:
            if self.side == PositionSide.LONG:
                # Adding to long
                new_qty = self.quantity + qty
                if new_qty != 0:
                    self.avg_cost = (self.avg_cost * self.quantity + price * qty) / new_qty
                self.quantity = new_qty
            elif self.side == PositionSide.SHORT:
                # Covering short
                if qty >= self.quantity:
                    # Fully covered, potentially flipping to long
                    remaining = qty - self.quantity
                    self.realized_pnl += (self.avg_cost - price) * self.quantity
                    self.quantity = remaining
                    if remaining > 0:
                        self.side = PositionSide.LONG
                        self.avg_cost = price
                else:
                    self.quantity -= qty
                    self.realized_pnl += (self.avg_cost - price) * qty
        else:  # SELL
            if self.side == PositionSide.SHORT:
                # Adding to short
                new_qty = self.quantity + qty
                if new_qty != 0:
                    self.avg_cost = (self.avg_cost * self.quantity + price * qty) / new_qty
                self.quantity = new_qty
            elif self.side == PositionSide.LONG:
                # Reducing long
                if qty >= self.quantity:
                    # Fully sold, potentially flipping to short
                    remaining = qty - self.quantity
                    self.realized_pnl += (price - self.avg_cost) * self.quantity
                    self.quantity = remaining
                    if remaining > 0:
                        self.side = PositionSide.SHORT
                        self.avg_cost = price
                else:
                    self.quantity -= qty
                    self.realized_pnl += (price - self.avg_cost) * qty
        
        self.last_updated = datetime.utcnow()


@dataclass
class CashBalance:
    """Cash balance in a currency."""
    currency: str
    amount: Decimal = Decimal('0')
    reserved: Decimal = Decimal('0')  # Reserved for pending orders
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def available(self) -> Decimal:
        return self.amount - self.reserved
    
    def reserve(self, amount: Decimal):
        self.reserved += amount
    
    def release(self, amount: Decimal):
        self.reserved = max(Decimal('0'), self.reserved - amount)
    
    def deposit(self, amount: Decimal):
        self.amount += amount
    
    def withdraw(self, amount: Decimal):
        if self.available >= amount:
            self.amount -= amount
            return True
        return False


@dataclass
class Transaction:
    """Executed transaction."""
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str = ""
    order_id: Optional[str] = None
    
    # Instrument
    figi: str = ""
    symbol: str = ""
    
    # Trade details
    side: TransactionSide = TransactionSide.BUY
    quantity: Decimal = Decimal('0')
    price: Decimal = Decimal('0')
    price_currency: str = "USD"
    
    # Fees & costs
    commission: Decimal = Decimal('0')
    commission_currency: str = "USD"
    fees: Decimal = Decimal('0')
    fees_currency: str = "USD"
    slippage: Optional[Decimal] = None
    slippage_currency: Optional[str] = None
    
    # Execution
    executed_at: datetime = field(default_factory=datetime.utcnow)
    status: TransactionStatus = TransactionStatus.FILLED
    
    # Broker info
    broker: Optional[str] = None
    exchange: Optional[str] = None
    execution_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def gross_amount(self) -> Decimal:
        return self.quantity * self.price
    
    @property
    def net_amount(self) -> Decimal:
        gross = self.gross_amount
        if self.side == TransactionSide.BUY:
            return gross + self.commission + self.fees
        else:
            return gross - self.commission - self.fees


@dataclass
class Order:
    """Pending or working order."""
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str = ""
    
    # Instrument
    figi: str = ""
    symbol: str = ""
    
    # Order details
    side: TransactionSide = TransactionSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Decimal('0')
    filled_quantity: Decimal = Decimal('0')
    
    # Pricing
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    trail_amount: Optional[Decimal] = None
    trail_percent: Optional[Decimal] = None
    
    # Timing
    time_in_force: TimeInForce = TimeInForce.DAY
    gtd_date: Optional[date] = None
    
    # Status
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Execution
    avg_fill_price: Optional[Decimal] = None
    commission: Decimal = Decimal('0')
    
    # Metadata
    broker: Optional[str] = None
    exchange: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity
    
    @property
    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity
    
    @property
    def is_active(self) -> bool:
        return self.status in [TransactionStatus.PENDING, TransactionStatus.PARTIAL]


@dataclass
class Portfolio:
    """Complete portfolio with positions, cash, and risk metrics."""
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    base_currency: str = "USD"
    
    # Holdings
    positions: Dict[str, Position] = field(default_factory=dict)  # figi -> Position
    cash_balances: Dict[str, CashBalance] = field(default_factory=dict)  # currency -> CashBalance
    
    # Orders
    orders: Dict[str, Order] = field(default_factory=dict)  # order_id -> Order
    transactions: List[Transaction] = field(default_factory=list)
    
    # Risk limits
    max_position_pct: Decimal = Decimal('0.20')  # 20% max per position
    max_sector_pct: Decimal = Decimal('0.40')    # 40% max per sector
    max_leverage: Decimal = Decimal('1.0')       # No leverage by default
    risk_budget: Optional[Dict[str, Decimal]] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_position(self, figi: str) -> Optional[Position]:
        return self.positions.get(figi)
    
    def get_cash(self, currency: str = None) -> CashBalance:
        currency = currency or self.base_currency
        if currency not in self.cash_balances:
            self.cash_balances[currency] = CashBalance(currency=currency)
        return self.cash_balances[currency]
    
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
    
    def add_transaction(self, transaction: Transaction):
        """Add transaction and update position."""
        self.transactions.append(transaction)
        
        # Update position
        if transaction.figi not in self.positions:
            self.positions[transaction.figi] = Position(
                portfolio_id=self.id,
                figi=transaction.figi,
                symbol=transaction.symbol,
                currency=transaction.price_currency
            )
        
        pos = self.positions[transaction.figi]
        pos.add_quantity(transaction.quantity, transaction.price, transaction.side)
        
        # Update cash
        cash = self.get_cash(transaction.price_currency)
        cash.amount += transaction.net_amount
        
        # Update order if linked
        if transaction.order_id and transaction.order_id in self.orders:
            order = self.orders[transaction.order_id]
            order.filled_quantity += transaction.quantity
            if order.is_filled:
                order.status = TransactionStatus.FILLED
                order.filled_at = transaction.executed_at
            else:
                order.status = TransactionStatus.PARTIAL
            order.updated_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    def add_order(self, order: Order):
        """Add new order."""
        self.orders[order.id] = order
        order.status = TransactionStatus.PENDING
        order.submitted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.is_active:
                order.status = TransactionStatus.CANCELLED
                order.updated_at = datetime.utcnow()
                return True
        return False
    
    def get_open_orders(self) -> List[Order]:
        return [o for o in self.orders.values() if o.is_active]
    
    def get_transactions(
        self,
        start: datetime = None,
        end: datetime = None,
        figi: str = None
    ) -> List[Transaction]:
        results = self.transactions
        if start:
            results = [t for t in results if t.executed_at >= start]
        if end:
            results = [t for t in results if t.executed_at <= end]
        if figi:
            results = [t for t in results if t.figi == figi]
        return sorted(results, key=lambda t: t.executed_at, reverse=True)
    
    def get_realized_pnl(
        self,
        start: datetime = None,
        end: datetime = None
    ) -> Decimal:
        pnl = Decimal('0')
        for t in self.get_transactions(start, end):
            pnl += t.net_amount if t.side == TransactionSide.SELL else -t.net_amount
        return pnl


@dataclass
class PortfolioSnapshot:
    """Point-in-time portfolio snapshot for reporting."""
    portfolio_id: str
    timestamp: datetime
    total_value: Decimal
    positions_value: Decimal
    cash_value: Decimal
    positions: Dict[str, Dict] = field(default_factory=dict)  # figi -> position snapshot
    cash_balances: Dict[str, Decimal] = field(default_factory=dict)
    weights: Dict[str, Decimal] = field(default_factory=dict)
    risk_metrics: Dict[str, Any] = field(default_factory=dict)


class PortfolioService:
    """Service for portfolio management operations."""
    
    def __init__(self, storage, market_data_service):
        self.storage = storage
        self.market_data = market_data_service
    
    async def create_portfolio(
        self,
        user_id: str,
        name: str,
        base_currency: str = "USD",
        initial_cash: Decimal = Decimal('0')
    ) -> Portfolio:
        """Create a new portfolio."""
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            base_currency=base_currency
        )
        
        if initial_cash > 0:
            portfolio.cash_balances[base_currency] = CashBalance(
                currency=base_currency,
                amount=initial_cash
            )
        
        # Save to storage
        # await self.storage.save_portfolio(portfolio)
        
        return portfolio
    
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Load portfolio from storage."""
        # return await self.storage.load_portfolio(portfolio_id)
        pass
    
    async def save_portfolio(self, portfolio: Portfolio):
        """Save portfolio to storage."""
        # await self.storage.save_portfolio(portfolio)
        pass
    
    async def update_market_prices(self, portfolio: Portfolio):
        """Update all position prices from market data."""
        symbols = [pos.symbol for pos in portfolio.positions.values()]
        if not symbols:
            return
        
        quotes = await self.market_data.get_quotes(symbols)
        for pos in portfolio.positions.values():
            if pos.figi in quotes:
                quote = quotes[pos.figi]
                if quote.last:
                    pos.update_price(quote.last.value)
        
        portfolio.updated_at = datetime.utcnow()
    
    async def take_snapshot(self, portfolio: Portfolio) -> PortfolioSnapshot:
        """Create a point-in-time snapshot."""
        await self.update_market_prices(portfolio)
        
        positions_snapshot = {}
        for figi, pos in portfolio.positions.items():
            positions_snapshot[figi] = {
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'avg_cost': pos.avg_cost,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                'side': pos.side.value
            }
        
        cash_snapshot = {c: cb.amount for c, cb in portfolio.cash_balances.items()}
        
        return PortfolioSnapshot(
            portfolio_id=portfolio.id,
            timestamp=datetime.utcnow(),
            total_value=portfolio.get_total_value(),
            positions_value=sum(p.market_value for p in portfolio.positions.values()),
            cash_value=sum(cb.amount for cb in portfolio.cash_balances.values()),
            positions=positions_snapshot,
            cash_balances=cash_snapshot,
            weights=portfolio.get_weights()
        )
    
    async def rebalance(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, Decimal],
        max_turnover: Decimal = Decimal('0.20'),
        transaction_cost_bps: Decimal = Decimal('10')
    ) -> List[Order]:
        """Generate rebalance orders."""
        # Update prices first
        await self.update_market_prices(portfolio)
        
        current_weights = portfolio.get_weights()
        total_value = portfolio.get_total_value()
        
        orders = []
        
        for figi, target_weight in target_weights.items():
            current_weight = current_weights.get(figi, Decimal('0'))
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) < Decimal('0.001'):  # Skip tiny differences
                continue
            
            target_value = total_value * target_weight
            current_value = total_value * current_weight
            trade_value = target_value - current_value
            
            # Get current price
            pos = portfolio.positions.get(figi)
            if not pos or not pos.current_price:
                continue
            
            trade_qty = trade_value / pos.current_price
            
            # Create order
            order = Order(
                portfolio_id=portfolio.id,
                figi=figi,
                symbol=pos.symbol,
                side=TransactionSide.BUY if trade_qty > 0 else TransactionSide.SELL,
                quantity=abs(trade_qty),
                order_type=OrderType.MARKET
            )
            
            orders.append(order)
        
        return orders