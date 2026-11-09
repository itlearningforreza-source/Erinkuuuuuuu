"""Order Management System - Order types, routing, execution, and lifecycle management."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    TRAILING_STOP_LIMIT = "TRAILING_STOP_LIMIT"
    MARKET_ON_CLOSE = "MARKET_ON_CLOSE"
    LIMIT_ON_CLOSE = "LIMIT_ON_CLOSE"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_TO_COVER = "BUY_TO_COVER"
    SELL_SHORT = "SELL_SHORT"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"          # Good Till Cancelled
    OPG = "OPG"          # Market On Open
    IOC = "IOC"          # Immediate or Cancel
    FOK = "FOK"          # Fill or Kill
    GTD = "GTD"          # Good Till Date
    GTT = "GTT"          # Good Till Time


class OrderStatus(str, Enum):
    PENDING_NEW = "PENDING_NEW"
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    PENDING_CANCEL = "PENDING_CANCEL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    CALCULATED = "CALCULATED"


class ExecutionType(str, Enum):
    NEW = "NEW"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILL = "FILL"
    CANCEL = "CANCEL"
    REJECT = "REJECT"
    EXPIRE = "EXPIRE"
    RESTATEMENT = "RESTATEMENT"


@dataclass
class Order:
    """Complete order representation."""
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = ""
    account_id: str = ""
    
    # Instrument
    figi: str = ""
    symbol: str = ""
    exchange: str = ""
    
    # Order details
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Decimal('0')
    filled_quantity: Decimal = Decimal('0')
    remaining_quantity: Decimal = Decimal('0')
    
    # Pricing
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    trail_amount: Optional[Decimal] = None
    trail_percent: Optional[Decimal] = None
    peg_offset: Optional[Decimal] = None
    
    # Timing
    time_in_force: TimeInForce = TimeInForce.DAY
    gtd_date: Optional[date] = None
    gtt_time: Optional[datetime] = None
    
    # Execution
    status: OrderStatus = OrderStatus.PENDING_NEW
    avg_fill_price: Optional[Decimal] = None
    last_fill_price: Optional[Decimal] = None
    last_fill_quantity: Optional[Decimal] = None
    
    # Costs
    commission: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    
    # Risk
    max_slippage_bps: Optional[int] = None
    max_participation_rate: Optional[Decimal] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    notes: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    # Execution reports
    executions: List[Dict] = field(default_factory=list)
    
    @property
    def is_active(self) -> bool:
        return self.status in [
            OrderStatus.PENDING_NEW,
            OrderStatus.NEW,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    @property
    def fill_rate(self) -> Decimal:
        if self.quantity == 0:
            return Decimal('0')
        return self.filled_quantity / self.quantity
    
    @property
    def notional_value(self) -> Decimal:
        if self.avg_fill_price:
            return self.filled_quantity * self.avg_fill_price
        return Decimal('0')


@dataclass
class ExecutionReport:
    """Individual execution/fill report."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    exec_id: str = ""
    
    # Trade details
    exec_type: ExecutionType = ExecutionType.NEW
    side: OrderSide = OrderSide.BUY
    quantity: Decimal = Decimal('0')
    price: Decimal = Decimal('0')
    
    # Venue
    exchange: str = ""
    venue: str = ""
    liquidity_indicator: str = ""  # MAKER, TAKER
    
    # Costs
    commission: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    
    # Timing
    exec_time: datetime = field(default_factory=datetime.utcnow)
    
    # Counterparty
    counterparty: str = ""
    
    # Reference
    trade_id: str = ""
    liquidity_flag: str = ""


class OrderManager:
    """Central order management system."""
    
    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._client_order_index: Dict[str, str] = {}  # client_order_id -> order_id
        self._account_orders: Dict[str, List[str]] = {}  # account_id -> [order_ids]
        self._execution_handlers: List[Callable] = []
        self._order_handlers: List[Callable] = []
    
    def create_order(
        self,
        account_id: str,
        figi: str,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        client_order_id: str = None,
        **kwargs
    ) -> Order:
        """Create a new order."""
        
        order = Order(
            account_id=account_id,
            figi=figi,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            remaining_quantity=quantity,
            client_order_id=client_order_id or str(uuid.uuid4()),
            **kwargs
        )
        
        self._orders[order.id] = order
        self._client_order_index[order.client_order_id] = order.id
        
        if account_id not in self._account_orders:
            self._account_orders[account_id] = []
        self._account_orders[account_id].append(order.id)
        
        # Trigger handlers
        self._notify_order_created(order)
        
        return order
    
    def submit_order(self, order_id: str) -> bool:
        """Submit order to exchange."""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if order.status != OrderStatus.PENDING_NEW:
            return False
        
        order.status = OrderStatus.NEW
        order.submitted_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        self._notify_order_update(order)
        return True
    
    def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """Cancel an active order."""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if not order.is_active:
            return False
        
        order.status = OrderStatus.PENDING_CANCEL
        order.updated_at = datetime.utcnow()
        
        # In real implementation, would send cancel request to exchange
        # For now, simulate immediate cancellation
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        
        self._notify_order_update(order)
        return True
    
    def replace_order(
        self,
        order_id: str,
        new_quantity: Optional[Decimal] = None,
        new_limit_price: Optional[Decimal] = None,
        new_stop_price: Optional[Decimal] = None
    ) -> Optional[Order]:
        """Replace (cancel/replace) an order."""
        order = self._orders.get(order_id)
        if not order or not order.is_active:
            return None
        
        # Cancel old order
        self.cancel_order(order_id)
        
        # Create new order with modifications
        new_order = Order(
            account_id=order.account_id,
            figi=order.figi,
            symbol=order.symbol,
            side=order.side,
            quantity=new_quantity or order.quantity,
            order_type=order.order_type,
            limit_price=new_limit_price if new_limit_price is not None else order.limit_price,
            stop_price=new_stop_price if new_stop_price is not None else order.stop_price,
            time_in_force=order.time_in_force,
            client_order_id=str(uuid.uuid4()),
        )
        
        self._orders[new_order.id] = new_order
        self._client_order_index[new_order.client_order_id] = new_order.id
        
        self._account_orders[order.account_id].append(new_order.id)
        
        self._notify_order_created(new_order)
        return new_order
    
    def process_execution(self, execution: ExecutionReport) -> bool:
        """Process an execution report from exchange."""
        order = self._orders.get(execution.order_id)
        if not order:
            return False
        
        # Update order
        order.filled_quantity += execution.quantity
        order.remaining_quantity = order.quantity - order.filled_quantity
        
        if execution.price:
            # Update average fill price
            if order.avg_fill_price is None:
                order.avg_fill_price = execution.price
            else:
                total_filled = order.filled_quantity
                prev_filled = total_filled - execution.quantity
                order.avg_fill_price = (
                    order.avg_fill_price * prev_filled + execution.price * execution.quantity
                ) / total_filled
        
        order.last_fill_price = execution.price
        order.last_fill_quantity = execution.quantity
        
        order.commission += Decimal(str(execution.commission))
        order.fees += Decimal(str(execution.fees))
        
        # Update status
        if order.remaining_quantity <= 0:
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()
        else:
            order.status = OrderStatus.PARTIALLY_FILLED
        
        order.updated_at = datetime.utcnow()
        
        # Store execution
        order.executions.append({
            'exec_id': execution.exec_id,
            'price': float(execution.price),
            'quantity': float(execution.quantity),
            'time': execution.exec_time.isoformat(),
            'commission': float(execution.commission),
            'fees': float(execution.fees),
            'exchange': execution.exchange,
        })
        
        self._notify_order_update(order)
        self._notify_execution(execution)
        
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)
    
    def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        order_id = self._client_order_index.get(client_order_id)
        if order_id:
            return self._orders.get(order_id)
        return None
    
    def get_account_orders(self, account_id: str, status: Optional[OrderStatus] = None) -> List[Order]:
        order_ids = self._account_orders.get(account_id, [])
        orders = [self._orders[oid] for oid in order_ids if oid in self._orders]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        return orders
    
    def get_active_orders(self, account_id: str = None) -> List[Order]:
        if account_id:
            return [o for o in self.get_account_orders(account_id) if o.is_active]
        return [o for o in self._orders.values() if o.is_active]
    
    def register_execution_handler(self, handler: Callable):
        self._execution_handlers.append(handler)
    
    def register_order_handler(self, handler: Callable):
        self._order_handlers.append(handler)
    
    def _notify_order_created(self, order: Order):
        for handler in self._order_handlers:
            try:
                handler('created', order)
            except Exception as e:
                pass  # Log error
    
    def _notify_order_update(self, order: Order):
        for handler in self._order_handlers:
            try:
                handler('update', order)
            except Exception as e:
                pass
    
    def _notify_execution(self, execution: ExecutionReport):
        for handler in self._execution_handlers:
            try:
                handler(execution)
            except Exception as e:
                pass


class SmartOrderRouter:
    """Smart order routing for best execution."""
    
    def __init__(self):
        self._venues: Dict[str, Dict] = {}
        self._routing_rules: List[Callable] = []
    
    def add_venue(
        self,
        venue_id: str,
        name: str,
        supported_order_types: List[str],
        fee_schedule: Dict,
        latency_ms: int = 1,
        liquidity_score: float = 0.5
    ):
        self._venues[venue_id] = {
            'name': name,
            'supported_order_types': supported_order_types,
            'fee_schedule': fee_schedule,
            'latency_ms': latency_ms,
            'liquidity_score': liquidity_score,
            'is_active': True
        }
    
    def route_order(self, order: Order) -> List[str]:
        """Determine best venue(s) for order."""
        # Filter active venues supporting order type
        candidates = [
            v for v in self._venues.values()
            if v['is_active'] and order.order_type.value in v['supported_order_types']
        ]
        
        if not candidates:
            return []
        
        # Score venues
        scored = []
        for venue in candidates:
            score = self._score_venue(venue, order)
            scored.append((venue['name'], score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [v[0] for v in scored]
    
    def _score_venue(self, venue: Dict, order: Order) -> float:
        """Score venue for order routing."""
        score = 0.0
        
        # Liquidity weight
        score += venue['liquidity_score'] * 0.4
        
        # Latency weight (lower is better)
        score += (1.0 / (1.0 + venue['latency_ms'] / 1000.0)) * 0.3
        
        # Fee weight (lower is better)
        fee = venue['fee_schedule'].get('maker' if order.side == 'BUY' else 'taker', 0.001)
        score += (1.0 / (1.0 + fee * 10000)) * 0.3
        
        return score


def create_order_manager() -> OrderManager:
    return OrderManager()

def create_smart_router() -> SmartOrderRouter:
    return SmartOrderRouter()