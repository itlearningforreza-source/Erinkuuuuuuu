"""Paper Trading Engine - Simulated live trading with realistic execution."""

import asyncio
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Optional
from enum import Enum
from typing import TYPE_CHECKING
from collections import deque
import threading

if TYPE_CHECKING:
    pass

from erin.market_intel.trading.oms import Order, OrderManager, OrderSide, OrderType, OrderStatus, TimeInForce, ExecutionReport, ExecutionType


class PaperTradingMode(str, Enum):
    SIMULATED = "SIMULATED"           # Pure simulation
    SHADOW = "SHADOW"                 # Shadow live orders
    REPLAY = "REPLAY"                 # Historical replay


@dataclass
class PaperTradingConfig:
    """Paper trading configuration."""
    mode: PaperTradingMode = PaperTradingMode.SIMULATED
    
    # Account
    initial_capital: Decimal = Decimal('100000')
    base_currency: str = "USD"
    allow_short: bool = False
    allow_margin: bool = False
    margin_requirement: Decimal = Decimal('0.50')
    maintenance_margin: Decimal = Decimal('0.25')
    
    # Execution
    commission_bps: Decimal = Decimal('5')
    slippage_bps: Decimal = Decimal('2')
    min_commission: Decimal = Decimal('1.00')
    
    # Market hours
    market_open: time = time(9, 30)
    market_close: time = time(16, 0)
    timezone: str = "America/New_York"
    
    # Data
    use_real_time_data: bool = False
    data_provider: str = "SIMULATED"
    
    # Risk limits
    max_position_pct: Decimal = Decimal('0.20')
    max_daily_loss: Decimal = Decimal('0.05')
    max_drawdown_pct: Decimal = Decimal('0.15')
    max_open_orders: int = 100
    
    # Logging
    log_trades: bool = True
    log_orders: bool = True
    log_level: str = "INFO"


@dataclass
class PaperAccount:
    """Paper trading account state."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Paper Account"
    currency: str = "USD"
    
    # Balances
    cash: Decimal = Decimal('0')
    buying_power: Decimal = Decimal('0')
    equity: Decimal = Decimal('0')
    initial_capital: Decimal = Decimal('0')
    
    # Positions
    positions: Dict[str, Dict] = field(default_factory=dict)
    
    # Risk metrics
    daily_pnl: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    peak_equity: Decimal = Decimal('0')
    
    # Risk limits
    max_position_pct: Decimal = Decimal('0.20')
    max_daily_loss: Decimal = Decimal('0.05')
    max_drawdown_pct: Decimal = Decimal('0.15')
    
    # Orders
    open_orders: List[str] = field(default_factory=list)
    order_history: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def net_liquidation_value(self) -> Decimal:
        return self.cash + sum(p.get('market_value', Decimal('0')) for p in self.positions.values())
    
    @property
    def daily_pnl_pct(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal('0')
        return self.daily_pnl / self.initial_capital
    
    @property
    def total_pnl_pct(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal('0')
        return (self.net_liquidation_value - self.initial_capital) / self.initial_capital


@dataclass
class MarketSnapshot:
    """Market data snapshot for simulation."""
    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    last: Decimal
    bid_size: int
    ask_size: int
    volume: int
    high: Decimal
    low: Decimal
    open: Decimal
    prev_close: Decimal


class SimulatedMarket:
    """Simulated market data feed."""
    
    def __init__(self, symbols: List[str], initial_prices: Dict[str, Decimal]):
        self.symbols = symbols
        self.prices = initial_prices.copy()
        self.volatilities = {s: Decimal('0.02') for s in symbols}
        self.drifts = {s: Decimal('0.0001') for s in symbols}
        self.subscribers: List[Callable] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._update_interval = 1.0  # seconds
    
    def subscribe(self, callback: Callable[[MarketSnapshot], None]):
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    async def start(self):
        """Start market simulation."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        self._running = False
        if self._task:
            await self._task
    
    async def _run_loop(self):
        while self._running:
            await self._generate_tick()
            await asyncio.sleep(self._update_interval)
    
    async def _generate_tick(self):
        """Generate a market tick for all symbols."""
        for symbol in self.symbols:
            # Geometric Brownian Motion
            price = self.prices[symbol]
            vol = self.volatilities[symbol]
            drift = self.drifts[symbol]
            
            dt = self._update_interval / (252 * 6.5 * 3600)  # trading seconds per year
            
            # GBM step
            z = np.random.normal(0, 1)
            price_change = price * (drift * Decimal(str(dt)) + vol * Decimal(str(math.sqrt(dt))) * Decimal(str(z)))
            
            new_price = max(price + price_change, Decimal('0.01'))
            self.prices[symbol] = new_price
            
            # Generate bid/ask
            spread = new_price * Decimal('0.0005')  # 5 bps spread
            bid = new_price - spread / 2
            ask = new_price + spread / 2
            
            snapshot = MarketSnapshot(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                bid=bid,
                ask=ask,
                last=new_price,
                bid_size=np.random.randint(100, 10000),
                ask_size=np.random.randint(100, 10000),
                volume=np.random.randint(100, 5000),
                high=new_price * Decimal('1.005'),
                low=new_price * Decimal('0.995'),
                open=new_price,
                prev_close=new_price,
            )
            
            # Notify subscribers
            for callback in self.subscribers:
                try:
                    await callback(snapshot)
                except Exception as e:
                    pass


class PaperTradingEngine:
    """Main paper trading engine."""
    
    def __init__(self, config: PaperTradingConfig):
        self.config = config
        self.account = PaperAccount(
            name=config.name if hasattr(config, 'name') else "Paper Account",
            currency=config.base_currency,
            cash=config.initial_capital,
            buying_power=config.initial_capital,
            equity=config.initial_capital,
            initial_capital=config.initial_capital,
            max_position_pct=config.max_position_pct,
            max_daily_loss=config.max_daily_loss,
            max_drawdown_pct=config.max_drawdown_pct,
        )
        
        self.order_manager = OrderManager()
        self.logger = logging.getLogger("paper_trading")
        self.logger.setLevel(getattr(logging, config.log_level))
        
        # Market data
        self.market_data: Dict[str, MarketSnapshot] = {}
        self.market_simulator: Optional[SimulatedMarket] = None
        
        # State
        self._running = False
        self._callbacks: Dict[str, List[Callable]] = {
            'on_order': [],
            'on_fill': [],
            'on_position_change': [],
            'on_account_update': [],
            'on_risk_alert': [],
        }
        
        # Order tracking
        self._pending_orders: Dict[str, Order] = {}
        self._order_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        
        # Market data
        self._market_task: Optional[asyncio.Task] = None
        self._data_subscribers: List[Callable] = []
    
    async def start(self, symbols: List[str] = None):
        """Start the paper trading engine."""
        if self._running:
            return
        
        self._running = True
        
        # Initialize account
        self.account.buying_power = self.account.cash
        self.account.equity = self.account.initial_capital
        self.account.peak_equity = self.account.initial_capital
        
        # Start market simulator if needed
        if self.config.use_real_time_data:
            # Would connect to real data provider
            pass
        else:
            # Start simulated market
            initial_prices = {s: Decimal('100') for s in (symbols or ['AAPL', 'MSFT', 'GOOGL'])}
            self.market_simulator = SimulatedMarket(
                symbols=symbols or ['AAPL', 'MSFT', 'GOOGL'],
                initial_prices=initial_prices
            )
            self.market_simulator.subscribe(self._on_market_update)
            await self.market_simulator.start()
        
        # Start order processing worker
        self._worker_task = asyncio.create_task(self._order_worker())
        
        self.logger.info("Paper trading engine started")
    
    async def stop(self):
        """Stop the paper trading engine."""
        self._running = False
        
        if self.market_simulator:
            await self.market_simulator.stop()
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        if self._market_task:
            self._market_task.cancel()
            try:
                await self._market_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Paper trading engine stopped")
    
    def _on_market_update(self, snapshot: MarketSnapshot):
        """Handle market data update."""
        self.market_data[snapshot.symbol] = snapshot
        self._update_positions(snapshot)
        self._check_orders(snapshot)
        self._update_account()
        
        # Notify subscribers
        for callback in self._data_subscribers:
            try:
                callback(snapshot)
            except Exception:
                pass
    
    def _update_positions(self, snapshot: MarketSnapshot):
        """Update position market values."""
        symbol = snapshot.symbol
        if symbol in self.account.positions:
            pos = self.account.positions[symbol]
            pos['current_price'] = snapshot.last
            pos['market_value'] = pos['quantity'] * snapshot.last
            pos['unrealized_pnl'] = (snapshot.last - pos['avg_cost']) * pos['quantity']
    
    def _check_orders(self, snapshot: MarketSnapshot):
        """Check and execute pending orders."""
        symbol = snapshot.symbol
        
        # Find pending orders for this symbol
        for order_id, order in list(self._pending_orders.items()):
            if order.figi != symbol and order.symbol != symbol:
                continue
            
            if not order.is_active:
                continue
            
            # Check if order should execute
            fill_price = self._get_fill_price(order, snapshot)
            if fill_price:
                self._execute_order(order, fill_price, snapshot.timestamp)
    
    def _get_fill_price(self, order: Order, snapshot: MarketSnapshot) -> Optional[Decimal]:
        """Determine fill price for order."""
        
        if order.order_type == OrderType.MARKET:
            if order.side == OrderSide.BUY:
                return snapshot.ask
            else:
                return snapshot.bid
        
        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and snapshot.ask <= order.limit_price:
                return min(snapshot.ask, order.limit_price)
            elif order.side == OrderSide.SELL and snapshot.bid >= order.limit_price:
                return max(snapshot.bid, order.limit_price)
            return None
        
        elif order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY and snapshot.last >= order.stop_price:
                return snapshot.ask  # Market order after trigger
            elif order.side == OrderSide.SELL and snapshot.last <= order.stop_price:
                return snapshot.bid
            return None
        
        return None
    
    def _execute_order(self, order: Order, fill_price: Decimal, timestamp: datetime):
        """Execute an order."""
        
        # Calculate costs
        notional = order.quantity * fill_price
        commission = max(
            notional * (self.config.commission_bps / Decimal('10000')),
            self.config.min_commission
        )
        slippage = notional * (self.config.slippage_bps / Decimal('10000'))
        
        # Check risk limits
        if not self._check_risk_limits(order, fill_price, commission + slippage):
            order.status = OrderStatus.REJECTED
            self._notify_order_update(order)
            return
        
        # Create execution report
        execution = ExecutionReport(
            order_id=order.id,
            exec_id=str(uuid.uuid4()),
            exec_type=ExecutionType.FILL,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            fees=slippage,
            exec_time=timestamp,
        )
        
        # Update order
        order.filled_quantity = order.quantity
        order.remaining_quantity = Decimal('0')
        order.avg_fill_price = fill_price
        order.last_fill_price = fill_price
        order.last_fill_quantity = order.quantity
        order.commission = commission
        order.fees = slippage
        order.status = OrderStatus.FILLED
        order.filled_at = timestamp
        order.updated_at = datetime.utcnow()
        order.executions.append({
            'exec_id': execution.exec_id,
            'price': float(fill_price),
            'quantity': float(order.quantity),
            'time': timestamp.isoformat(),
            'commission': float(commission),
            'fees': float(slippage),
        })
        
        # Update account
        self._update_account_on_fill(order, fill_price, commission, slippage)
        
        # Remove from pending
        if order.id in self._pending_orders:
            del self._pending_orders[order.id]
        
        # Notify
        self._notify_order_update(order)
        self._notify_fill(execution)
        
        self.logger.info(f"Order filled: {order.symbol} {order.side} {order.quantity} @ {fill_price}")
    
    def _check_risk_limits(self, order: Order, price: Decimal, costs: Decimal) -> bool:
        """Check if order passes risk limits."""
        
        notional = order.quantity * price
        
        # Check position size limit
        if order.side == OrderSide.BUY:
            new_position_value = notional
            current_pos = self.account.positions.get(order.symbol, {})
            current_value = current_pos.get('market_value', Decimal('0'))
            total_value = current_value + notional
            
            if total_value > self.account.equity * self.config.max_position_pct:
                self.logger.warning(f"Position size limit exceeded for {order.symbol}")
                return False
            
            # Check cash
            total_cost = notional + costs
            if self.account.cash < total_cost:
                self.logger.warning(f"Insufficient cash for {order.symbol}")
                return False
        
        elif order.side == OrderSide.SELL:
            position = self.account.positions.get(order.symbol, {})
            current_qty = position.get('quantity', Decimal('0'))
            if current_qty < order.quantity:
                self.logger.warning(f"Insufficient position for {order.symbol}")
                return False
        
        # Check daily loss limit
        if self.account.daily_pnl < -self.account.initial_capital * self.config.max_daily_loss:
            self.logger.warning("Daily loss limit exceeded")
            return False
        
        # Check max drawdown
        if self.account.max_drawdown > self.account.peak_equity * self.config.max_drawdown_pct:
            self.logger.warning("Max drawdown limit exceeded")
            return False
        
        return True
    
    def _update_account_on_fill(self, order: Order, fill_price: Decimal, commission: Decimal, slippage: Decimal):
        """Update account balances after fill."""
        
        notional = order.quantity * fill_price
        total_cost = notional + commission + slippage
        
        if order.side == OrderSide.BUY:
            self.account.cash -= total_cost
            
            # Update position
            if order.symbol not in self.account.positions:
                self.account.positions[order.symbol] = {
                    'quantity': Decimal('0'),
                    'avg_cost': Decimal('0'),
                    'market_value': Decimal('0'),
                    'unrealized_pnl': Decimal('0'),
                }
            
            pos = self.account.positions[order.symbol]
            new_qty = pos['quantity'] + order.quantity
            new_avg = ((pos['avg_cost'] * pos['quantity']) + (fill_price * order.quantity)) / new_qty if new_qty != 0 else fill_price
            
            pos['quantity'] = new_qty
            pos['avg_cost'] = new_avg
            pos['market_value'] = new_qty * fill_price
            pos['unrealized_pnl'] = (fill_price - new_avg) * new_qty
            
        elif order.side == OrderSide.SELL:
            self.account.cash += notional - costs
            
            # Update position
            pos = self.account.positions.get(order.symbol, {})
            if pos:
                pos['quantity'] -= order.quantity
                pos['market_value'] = pos['quantity'] * fill_price
                pos['unrealized_pnl'] = (fill_price - pos['avg_cost']) * pos['quantity']
                
                if pos['quantity'] <= 0:
                    del self.account.positions[order.symbol]
                    self.account.realized_pnl += (fill_price - pos['avg_cost']) * order.quantity - commission - slippage
        
        self._update_account()
    
    def _update_account(self):
        """Update account metrics."""
        self.account.unrealized_pnl = sum(
            p.get('unrealized_pnl', Decimal('0')) for p in self.account.positions.values()
        )
        self.account.equity = self.account.net_liquidation_value
        
        # Update peak
        if self.account.equity > self.account.peak_equity:
            self.account.peak_equity = self.account.equity
        
        # Update drawdown
        if self.account.peak_equity > 0:
            self.account.max_drawdown = (self.account.peak_equity - self.account.equity) / self.account.peak_equity
        
        self.account.buying_power = self.account.cash  # Simplified
        self.account.last_updated = datetime.utcnow()
        
        # Check risk alerts
        self._check_risk_alerts()
        
        # Notify
        for callback in self._callbacks['on_account_update']:
            try:
                callback(self.account)
            except Exception:
                pass
    
    def _check_risk_alerts(self):
        """Check for risk limit breaches."""
        
        # Daily loss
        if self.account.daily_pnl_pct < -self.config.max_daily_loss:
            self._notify_risk_alert('DAILY_LOSS_LIMIT', f"Daily loss limit exceeded: {self.account.daily_pnl_pct:.2%}")
        
        # Drawdown
        if self.account.max_drawdown > self.config.max_drawdown_pct:
            self._notify_risk_alert('MAX_DRAWDOWN', f"Max drawdown exceeded: {self.account.max_drawdown:.2%}")
        
        # Position concentration
        for symbol, pos in self.account.positions.items():
            if pos.get('market_value', 0) > self.account.equity * self.config.max_position_pct:
                self._notify_risk_alert('POSITION_CONCENTRATION', f"Position {symbol} exceeds limit: {pos['market_value'] / self.account.equity:.2%}")
    
    def _notify_risk_alert(self, alert_type: str, message: str):
        for callback in self._callbacks['on_risk_alert']:
            try:
                callback(alert_type, message)
            except Exception:
                pass
    
    def _notify_order_update(self, order: Order):
        for callback in self._callbacks['on_order']:
            try:
                callback(order)
            except Exception:
                pass
    
    def _notify_fill(self, execution: ExecutionReport):
        for callback in self._callbacks['on_fill']:
            try:
                callback(execution)
            except Exception:
                pass
    
    def register_callback(self, event: str, callback: Callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        **kwargs
    ) -> Order:
        """Place a new order."""
        
        order = self.order_manager.create_order(
            account_id=self.account.id,
            figi=symbol,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            **kwargs
        )
        
        # Add to pending
        self._pending_orders[order.id] = order
        
        # Submit immediately
        self.order_manager.submit_order(order.id)
        
        return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.order_manager.cancel_order(order_id)
    
    def get_market_data(self, symbol: str) -> Optional[MarketSnapshot]:
        return self.market_data.get(symbol)
    
    def get_account(self) -> PaperAccount:
        return self.account
    
    def get_positions(self) -> Dict:
        return self.account.positions.copy()
    
    def get_open_orders(self) -> List[Order]:
        return [o for o in self._pending_orders.values() if o.is_active]
    
    def register_data_subscriber(self, callback: Callable):
        self._data_subscribers.append(callback)
    
    def register_callback(self, event: str, callback: Callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics."""
        return {
            'equity': float(self.account.equity),
            'cash': float(self.account.cash),
            'buying_power': float(self.account.buying_power),
            'daily_pnl': float(self.account.daily_pnl),
            'daily_pnl_pct': float(self.account.daily_pnl_pct),
            'total_pnl': float(self.account.net_liquidation_value - self.account.initial_capital),
            'total_pnl_pct': float(self.account.total_pnl_pct),
            'unrealized_pnl': float(self.account.unrealized_pnl),
            'realized_pnl': float(self.account.realized_pnl),
            'max_drawdown': float(self.account.max_drawdown),
            'peak_equity': float(self.account.peak_equity),
            'positions': len(self.account.positions),
            'open_orders': len(self.account.open_orders),
        }
    
    def reset_daily_pnl(self):
        """Reset daily P&L (call at market open)."""
        self.account.daily_pnl = Decimal('0')
    
    async def close_position(self, symbol: str, quantity: Decimal = None) -> Optional[Order]:
        """Close an existing position."""
        if symbol not in self.account.positions:
            return None
        
        pos = self.account.positions[symbol]
        qty = quantity or pos['quantity']
        
        if qty <= 0:
            return None
        
        side = OrderSide.SELL if pos['quantity'] > 0 else OrderSide.BUY
        return await self.place_order(symbol, side, qty, OrderType.MARKET)
    
    async def close_all_positions(self) -> List[Order]:
        """Close all open positions."""
        orders = []
        for symbol, pos in list(self.account.positions.items()):
            if pos['quantity'] != 0:
                side = OrderSide.SELL if pos['quantity'] > 0 else OrderSide.BUY
                order = await self.place_order(symbol, side, abs(pos['quantity']), OrderType.MARKET)
                if order:
                    orders.append(order)
        return orders
    
    def subscribe_market_data(self, callback: Callable):
        self._data_subscribers.append(callback)
    
    def unsubscribe_market_data(self, callback: Callable):
        if callback in self._data_subscribers:
            self._data_subscribers.remove(callback)
    
    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now().time()
        return self.config.market_open <= now <= self.config.market_close
    
    async def run_for_duration(self, duration_seconds: int):
        """Run for specified duration."""
        await asyncio.sleep(duration_seconds)


def create_paper_trading_config(
    initial_capital: Decimal = Decimal('100000'),
    mode: PaperTradingMode = PaperTradingMode.SIMULATED,
    **kwargs
) -> PaperTradingConfig:
    return PaperTradingConfig(
        initial_capital=initial_capital,
        mode=mode,
        **kwargs
    )


def create_paper_trading_engine(config: PaperTradingConfig) -> PaperTradingEngine:
    return PaperTradingEngine(config)


# Example usage and testing
async def run_paper_trading_example():
    """Example of running paper trading."""
    
    config = create_paper_trading_config(
        initial_capital=Decimal('100000'),
        mode=PaperTradingMode.SIMULATED,
        commission_bps=Decimal('5'),
        slippage_bps=Decimal('2'),
    )
    
    engine = create_paper_trading_engine(config)
    
    # Register callbacks
    def on_fill(execution):
        print(f"FILL: {execution.symbol} {execution.side} {execution.quantity} @ {execution.price}")
    
    def on_account(account):
        print(f"Account: Equity={account.equity:.2f}, PnL={account.total_pnl_pct:.2%}")
    
    engine.register_callback('on_fill', on_fill)
    engine.register_callback('on_account_update', on_account)
    
    # Start engine
    await engine.start(symbols=['AAPL', 'MSFT', 'GOOGL'])
    
    # Place some orders
    await engine.place_order('AAPL', OrderSide.BUY, Decimal('10'), OrderType.MARKET)
    await engine.place_order('MSFT', OrderSide.BUY, Decimal('5'), OrderType.LIMIT, limit_price=Decimal('300'))
    
    # Run for 30 seconds
    await engine.run_for_duration(30)
    
    # Check performance
    metrics = engine.get_performance_metrics()
    print(f"Final metrics: {metrics}")
    
    # Close all
    await engine.close_all_positions()
    
    await engine.stop()