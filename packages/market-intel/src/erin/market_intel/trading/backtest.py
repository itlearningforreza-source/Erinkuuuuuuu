"""Event-Driven Backtesting Engine - Bar-by-bar simulation with realistic execution."""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Tuple, Iterator
from enum import Enum
from typing import TYPE_CHECKING
import warnings
import copy

if TYPE_CHECKING:
    pass


class BacktestMode(str, Enum):
    VECTORIZED = "VECTORIZED"      # Fast vectorized backtest
    EVENT_DRIVEN = "EVENT_DRIVEN"  # Bar-by-bar event-driven
    WALK_FORWARD = "WALK_FORWARD"  # Walk-forward optimization


class DataFrequency(str, Enum):
    TICK = "TICK"
    SECOND = "SECOND"
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


@dataclass
class BacktestConfig:
    """Backtest configuration."""
    start_date: date
    end_date: date
    initial_capital: Decimal = Decimal('1000000')
    base_currency: str = "USD"
    
    # Execution
    commission_bps: Decimal = Decimal('5')  # 5 bps per side
    slippage_bps: Decimal = Decimal('2')    # 2 bps slippage
    min_commission: Decimal = Decimal('1.00')
    
    # Risk limits
    max_position_pct: Decimal = Decimal('0.20')
    max_sector_pct: Decimal = Decimal('0.40')
    max_leverage: Decimal = Decimal('1.0')
    max_drawdown_pct: Decimal = Decimal('0.20')
    
    # Data
    data_frequency: DataFrequency = DataFrequency.DAY
    warmup_periods: int = 0
    
    # Execution
    allow_short: bool = False
    allow_margin: bool = False
    interest_rate: Decimal = Decimal('0.05')
    
    # Reporting
    benchmark_symbol: str = "SPY"
    generate_tear_sheet: bool = True


@dataclass
class PortfolioState:
    """Portfolio state at a point in time."""
    timestamp: datetime
    cash: Decimal
    positions: Dict[str, Decimal]  # symbol -> quantity
    position_values: Dict[str, Decimal]  # symbol -> market value
    total_value: Decimal
    returns: Decimal
    drawdown: Decimal
    peak_value: Decimal


@dataclass
class Trade:
    """Individual trade record."""
    timestamp: datetime
    symbol: str
    side: str  # BUY/SELL
    quantity: Decimal
    price: Decimal
    commission: Decimal
    slippage: Decimal
    order_id: str
    strategy_id: str = ""


@dataclass
class BacktestResult:
    """Complete backtest result."""
    config: 'BacktestConfig'
    
    # Portfolio history
    portfolio_history: List[PortfolioState]
    trades: List[Trade]
    
    # Performance metrics
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    max_drawdown: Decimal
    max_drawdown_duration: int
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    profit_factor: Decimal
    avg_trade_duration: Decimal
    
    # Risk metrics
    var_95: Decimal
    es_95: Decimal
    beta: Decimal
    alpha: Decimal
    information_ratio: Decimal
    
    # Benchmark comparison
    benchmark_return: Decimal
    excess_return: Decimal
    tracking_error: Decimal
    
    # Execution
    total_commission: Decimal
    total_slippage: Decimal
    turnover: Decimal
    
    # Metadata
    start_date: date
    end_date: date
    duration_days: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_return': float(self.total_return),
            'annualized_return': float(self.annualized_return),
            'volatility': float(self.volatility),
            'sharpe_ratio': float(self.sharpe_ratio),
            'sortino_ratio': float(self.sortino_ratio),
            'calmar_ratio': float(self.calmar_ratio),
            'max_drawdown': float(self.max_drawdown),
            'win_rate': float(self.win_rate),
            'profit_factor': float(self.profit_factor),
            'total_trades': self.total_trades,
            'sharpe_ratio': float(self.sharpe_ratio),
        }


class DataPortal:
    """Data access for backtesting."""
    
    def __init__(self):
        self._price_data: Dict[str, pd.DataFrame] = {}
        self._fundamental_data: Dict[str, Dict] = {}
        self._calendar: List[date] = []
    
    def add_price_data(self, symbol: str, data: pd.DataFrame):
        """Add price data for a symbol.
        
        DataFrame should have columns: open, high, low, close, volume
        Index should be DatetimeIndex
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must have columns: {required_cols}")
        
        self._price_data[symbol] = data.sort_index()
    
    def get_price(
        self,
        symbol: str,
        timestamp: datetime,
        field: str = 'close'
    ) -> Optional[Decimal]:
        """Get price for symbol at timestamp."""
        if symbol not in self._price_data:
            return None
        
        data = self._price_data[symbol]
        
        # Find nearest timestamp <= requested
        idx = data.index.searchsorted(timestamp, side='right') - 1
        if idx < 0:
            return None
        
        if idx >= len(data):
            idx = len(data) - 1
        
        return Decimal(str(data.iloc[idx][field]))
    
    def get_bar(self, symbol: str, timestamp: datetime) -> Optional[Dict]:
        """Get full OHLCV bar."""
        if symbol not in self._price_data:
            return None
        
        data = self._price_data[symbol]
        idx = data.index.searchsorted(timestamp, side='right') - 1
        
        if idx < 0 or idx >= len(data):
            return None
        
        bar = data.iloc[idx]
        return {
            'open': Decimal(str(bar['open'])),
            'high': Decimal(str(bar['high'])),
            'low': Decimal(str(bar['low'])),
            'close': Decimal(str(bar['close'])),
            'volume': int(bar['volume']),
        }
    
    def get_history(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        fields: List[str] = None
    ) -> pd.DataFrame:
        """Get historical data range."""
        if symbol not in self._price_data:
            return pd.DataFrame()
        
        data = self._price_data[symbol]
        mask = (data.index >= start) & (data.index <= end)
        result = data.loc[mask]
        
        if fields:
            result = result[fields]
        
        return result
    
    def get_universe(self, timestamp: datetime) -> List[str]:
        """Get available symbols at timestamp."""
        return list(self._price_data.keys())
    
    def get_calendar(self, start: date, end: date) -> List[date]:
        """Get trading calendar."""
        if self._calendar:
            return [d for d in self._calendar if start <= d <= end]
        
        # Generate from price data
        all_dates = set()
        for df in self._price_data.values():
            all_dates.update([d.date() for d in df.index])
        
        self._calendar = sorted(all_dates)
        return [d for d in self._calendar if start <= d <= end]


class Strategy:
    """Base strategy class."""
    
    def __init__(self, name: str = "Strategy"):
        self.name = name
        self.params: Dict = {}
        self.state: Dict = {}
    
    def initialize(self, data_portal: DataPortal, portfolio: 'Portfolio'):
        """Initialize strategy."""
        pass
    
    def on_bar(self, timestamp: datetime, data_portal: DataPortal, portfolio: 'Portfolio'):
        """Called on each bar."""
        pass
    
    def on_fill(self, trade: Trade):
        """Called when order is filled."""
        pass
    
    def on_order_update(self, order: 'Order'):
        """Called when order status changes."""
        pass
    
    def generate_signals(self, timestamp: datetime, data_portal: DataPortal) -> Dict[str, Decimal]:
        """Generate target weights for each symbol."""
        return {}
    
    def finalize(self):
        """Cleanup at end of backtest."""
        pass


class Portfolio:
    """Backtest portfolio with realistic execution."""
    
    def __init__(self, initial_capital: Decimal, base_currency: str = "USD"):
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.base_currency = base_currency
        self.positions: Dict[str, Decimal] = {}
        self.cost_basis: Dict[str, Decimal] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, Decimal]] = []
    
    def get_position(self, symbol: str) -> Decimal:
        return self.positions.get(symbol, Decimal('0'))
    
    def get_market_value(self, prices: Dict[str, Decimal]) -> Decimal:
        total = self.cash
        for symbol, qty in self.positions.items():
            if qty != 0 and symbol in prices:
                total += qty * prices[symbol]
        return total
    
    def get_pnl(self, prices: Dict[str, Decimal]) -> Decimal:
        return self.get_market_value(prices) - self.initial_capital
    
    def record_trade(self, trade: Trade):
        self.trades.append(trade)
        
        # Update position
        symbol = trade.symbol
        if trade.side == 'BUY':
            self.positions[symbol] = self.positions.get(symbol, Decimal('0')) + trade.quantity
            # Update cost basis
            current_qty = self.positions[symbol] - trade.quantity
            current_basis = self.cost_basis.get(symbol, Decimal('0'))
            new_basis = (current_basis * current_qty + trade.price * trade.quantity) / (current_qty + trade.quantity) if (current_qty + trade.quantity) != 0 else trade.price
            self.cost_basis[symbol] = new_basis
        else:
            self.positions[symbol] = self.positions.get(symbol, Decimal('0')) - trade.quantity
            if self.positions[symbol] == 0:
                del self.positions[symbol]
                if symbol in self.cost_basis:
                    del self.cost_basis[symbol]
        
        # Update cash
        cost = trade.quantity * trade.price + trade.commission + trade.slippage
        if trade.side == 'BUY':
            self.cash -= cost
        else:
            self.cash += trade.quantity * trade.price - trade.commission - trade.slippage


class ExecutionSimulator:
    """Realistic execution simulation."""
    
    def __init__(self, config):
        self.commission_bps = config.commission_bps
        self.slippage_bps = config.slippage_bps
        self.min_commission = config.min_commission
        self.allow_short = config.allow_short
    
    def execute_order(
        self,
        order: 'Order',
        bar: Dict,
        portfolio: Portfolio,
        timestamp: datetime
    ) -> Optional[Trade]:
        """Simulate order execution."""
        
        if order.side == 'BUY':
            price = Decimal(str(bar['high']))  # Buy at high (conservative)
        else:
            price = Decimal(str(bar['low']))   # Sell at low (conservative)
        
        # Apply slippage
        slippage = price * (self.slippage_bps / Decimal('10000'))
        if order.side == 'BUY':
            exec_price = price + slippage
        else:
            exec_price = price - slippage
        
        # Check if we have enough cash/position
        if order.side == 'BUY':
            cost = exec_price * order.quantity
            commission = max(cost * (self.commission_bps / Decimal('10000')), Decimal('1.00'))
            total_cost = cost + commission
            if portfolio.cash < total_cost:
                return None  # Not enough cash
        else:
            position = portfolio.get_position(order.symbol)
            if position < order.quantity:
                return None  # Not enough position (no short allowed)
        
        # Calculate costs
        cost = exec_price * order.quantity
        commission = max(cost * (self.commission_bps / Decimal('10000')), Decimal('1.00'))
        slippage_cost = slippage * order.quantity
        
        # Create trade
        trade = Trade(
            timestamp=timestamp,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=exec_price,
            commission=commission,
            slippage=slippage_cost,
            order_id=str(uuid.uuid4()),
        )
        
        return trade


class EventDrivenBacktester:
    """Event-driven backtesting engine."""
    
    def __init__(self, config: BacktestConfig, data_portal: DataPortal):
        self.config = config
        self.data_portal = data_portal
        self.portfolio = Portfolio(config.initial_capital, config.base_currency)
        self.execution_sim = ExecutionSimulator(config)
        
        # State
        self.current_time: Optional[datetime] = None
        self.current_prices: Dict[str, Decimal] = {}
        self.orders: Dict[str, Any] = {}
        self.active_strategies: List[Strategy] = []
        
        # Results
        self.portfolio_history: List[PortfolioState] = []
        self.trades: List[Trade] = []
        self.orders: List[Any] = []
        
        # Performance
        self.start_time = None
        self.end_time = None
    
    def add_strategy(self, strategy: Strategy):
        self.active_strategies.append(strategy)
    
    def run(self) -> BacktestResult:
        """Run the backtest."""
        self.start_time = datetime.utcnow()
        
        # Initialize strategies
        for strategy in self.active_strategies:
            strategy.initialize(self.data_portal, self.portfolio)
        
        # Get trading calendar
        calendar = self.data_portal.get_calendar(self.config.start_date, self.config.end_date)
        
        # Warmup period
        warmup_end = self.config.start_date + timedelta(days=self.config.warmup_periods)
        
        for current_date in calendar:
            if current_date < self.config.start_date:
                continue
            if current_date > self.config.end_date:
                break
            
            self.current_time = datetime.combine(current_date, datetime.min.time())
            
            # Update prices
            self._update_prices()
            
            # Record portfolio state
            self._record_portfolio_state()
            
            # Skip strategy execution during warmup
            if current_date <= warmup_end:
                continue
            
            # Run strategies
            self._run_strategies()
            
            # Process pending orders
            self._process_orders()
        
        self.end_time = datetime.utcnow()
        
        return self._generate_result()
    
    def _update_prices(self):
        """Update current prices for all symbols."""
        self.current_prices = {}
        for symbol in self.data_portal.get_universe(self.current_time):
            price = self.data_portal.get_price(symbol, self.current_time)
            if price is not None:
                self.current_prices[symbol] = price
    
    def _record_portfolio_state(self):
        """Record current portfolio state."""
        position_values = {}
        for symbol, qty in self.portfolio.positions.items():
            if qty != 0 and symbol in self.current_prices:
                position_values[symbol] = qty * self.current_prices[symbol]
        
        total_value = self.portfolio.get_market_value(self.current_prices)
        returns = (total_value - self.portfolio.initial_capital) / self.portfolio.initial_capital
        
        peak = max([s.total_value for s in self.portfolio_history] + [total_value]) if self.portfolio_history else total_value
        drawdown = (peak - total_value) / peak if peak > 0 else Decimal('0')
        
        state = PortfolioState(
            timestamp=self.current_time,
            cash=self.portfolio.cash,
            positions=self.portfolio.positions.copy(),
            position_values=position_values,
            total_value=total_value,
            returns=returns,
            drawdown=drawdown,
            peak_value=peak
        )
        
        self.portfolio_history.append(state)
        self.portfolio.equity_curve.append((self.current_time, total_value))
    
    def _run_strategies(self):
        """Run all active strategies."""
        for strategy in self.active_strategies:
            try:
                strategy.on_bar(self.current_time, self.data_portal, self.portfolio)
            except Exception as e:
                warnings.warn(f"Strategy {strategy.name} error: {e}")
    
    def _process_orders(self):
        """Process pending orders."""
        # In a real implementation, would check order book
        pass
    
    def _generate_result(self) -> BacktestResult:
        """Generate final backtest result."""
        if not self.portfolio_history:
            raise ValueError("No portfolio history generated")
        
        # Calculate returns series
        equity = [s.total_value for s in self.portfolio_history]
        returns = np.diff(equity) / equity[:-1]
        
        # Total return
        total_return = (equity[-1] - equity[0]) / equity[0]
        
        # Annualized return
        days = (self.config.end_date - self.config.start_date).days
        years = days / 365.25
        annualized_return = (Decimal('1') + total_return) ** (Decimal('1') / Decimal(str(years))) - Decimal('1')
        
        # Volatility (annualized)
        volatility = Decimal(str(np.std(returns) * np.sqrt(252)))
        
        # Sharpe ratio
        risk_free = Decimal('0.02')  # 2% annual
        excess_return = annualized_return - risk_free
        sharpe = excess_return / volatility if volatility > 0 else Decimal('0')
        
        # Sortino ratio
        negative_returns = [r for r in returns if r < 0]
        downside_vol = Decimal(str(np.std(negative_returns) * np.sqrt(252))) if negative_returns else Decimal('0')
        sortino = excess_return / downside_vol if downside_vol > 0 else Decimal('0')
        
        # Max drawdown
        equity_arr = np.array([float(e) for e in equity])
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / peak
        max_drawdown = Decimal(str(abs(np.min(drawdown))))
        
        # Max drawdown duration
        in_drawdown = drawdown < 0
        dd_durations = []
        current_duration = 0
        for d in in_drawdown:
            if d:
                current_duration += 1
            else:
                if current_duration > 0:
                    dd_durations.append(current_duration)
                current_duration = 0
        max_dd_duration = max(dd_durations) if dd_durations else 0
        
        # Trade statistics
        trades = self.trades
        winning = [t for t in trades if self._is_winning_trade(t)]
        losing = [t for t in trades if not self._is_winning_trade(t)]
        
        total_trades = len(trades)
        winning_trades = len(winning)
        losing_trades = len(losing)
        win_rate = Decimal(str(winning_trades / total_trades)) if total_trades > 0 else Decimal('0')
        
        avg_win = Decimal(str(np.mean([float(t.price * t.quantity) for t in winning]))) if winning else Decimal('0')
        avg_loss = Decimal(str(np.mean([float(t.price * t.quantity) for t in losing]))) if losing else Decimal('0')
        
        gross_profit = sum(float(t.price * t.quantity) for t in winning)
        gross_loss = abs(sum(float(t.price * t.quantity) for t in losing))
        profit_factor = Decimal(str(gross_profit / gross_loss)) if gross_loss > 0 else Decimal('inf')
        
        # Calmar ratio
        calmar = annualized_return / max_drawdown if max_drawdown > 0 else Decimal('0')
        
        # VaR and ES
        var_95 = Decimal(str(np.percentile(returns, 5))) * Decimal(str(np.sqrt(252)))
        es_95 = Decimal(str(np.mean([r for r in returns if r <= np.percentile(returns, 5)]))) * Decimal(str(np.sqrt(252))) if returns else Decimal('0')
        
        # Total costs
        total_commission = sum(Decimal(str(t.commission)) for t in self.trades)
        total_slippage = sum(Decimal(str(t.slippage)) for t in self.trades)
        
        return BacktestResult(
            config=self.config,
            portfolio_history=self.portfolio_history,
            trades=self.trades,
            total_return=Decimal(str((equity[-1] - equity[0]) / equity[0])),
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_trade_duration=Decimal('0'),
            var_95=var_95,
            es_95=es_95,
            beta=Decimal('0'),
            alpha=Decimal('0'),
            information_ratio=Decimal('0'),
            benchmark_return=Decimal('0'),
            excess_return=Decimal('0'),
            tracking_error=Decimal('0'),
            total_commission=Decimal('0'),
            total_slippage=Decimal('0'),
            turnover=Decimal('0'),
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            duration_days=(self.config.end_date - self.config.start_date).days
        )
    
    def _is_winning_trade(self, trade: Trade) -> bool:
        # Simplified - would need matching buy/sell
        return trade.side == 'SELL'  # Simplified


class VectorizedBacktester:
    """Fast vectorized backtesting for simple strategies."""
    
    def __init__(self, config: BacktestConfig, data_portal: DataPortal):
        self.config = config
        self.data_portal = data_portal
    
    def run(self, signals: pd.DataFrame) -> BacktestResult:
        """Run vectorized backtest on pre-computed signals.
        
        Args:
            signals: DataFrame with signal values for each symbol/date
                    Index: DatetimeIndex, Columns: symbols, Values: target weights
        """
        # Implementation for vectorized backtest
        pass


class WalkForwardOptimizer:
    """Walk-forward optimization for strategy parameters."""
    
    def __init__(
        self,
        config: BacktestConfig,
        data_portal: DataPortal,
        strategy_class: type,
        param_grid: Dict[str, List],
        train_window: int = 252,
        test_window: int = 63,
        step: int = 21
    ):
        self.config = config
        self.data_portal = data_portal
        self.strategy_class = strategy_class
        self.param_grid = param_grid
        self.train_window = train_window
        self.test_window = test_window
        self.step = step
    
    def optimize(self) -> Dict:
        """Run walk-forward optimization."""
        # Implementation would iterate through train/test windows
        # and find best parameters for each window
        pass


def create_backtest_config(
    start_date: date,
    end_date: date,
    initial_capital: Decimal = Decimal('1000000'),
    **kwargs
) -> BacktestConfig:
    return BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        **kwargs
    )


def create_data_portal() -> DataPortal:
    return DataPortal()


def create_backtester(config: BacktestConfig, data_portal: DataPortal) -> EventDrivenBacktester:
    return EventDrivenBacktester(config, data_portal)