"""ERIN Market Intelligence - Trading Module."""

from erin.market_intel.trading.oms import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
    ExecutionReport,
    ExecutionType,
    OrderManager,
    SmartOrderRouter,
    create_order_manager,
    create_smart_router,
)

from erin.market_intel.trading.backtest import (
    BacktestConfig,
    BacktestMode,
    DataFrequency,
    DataPortal,
    Strategy,
    Portfolio,
    ExecutionSimulator,
    EventDrivenBacktester,
    VectorizedBacktester,
    WalkForwardOptimizer,
    BacktestResult,
    PortfolioState,
    Trade,
    create_backtest_config,
    create_data_portal,
    create_backtester,
)

from erin.market_intel.trading.tca import (
    TCAConfig,
    SlippageModel,
    ExecutionMetrics,
    OrderTCA,
    MarketImpactModel,
    TCACalculator,
    PerformanceAttribution,
    create_tca_config,
    create_tca_calculator,
    create_market_impact_model,
)

from erin.market_intel.trading.paper_trading import (
    PaperTradingConfig,
    PaperTradingMode,
    PaperAccount,
    MarketSnapshot,
    SimulatedMarket,
    PaperTradingEngine,
    create_paper_trading_config,
    create_paper_trading_engine,
)

__all__ = [
    # OMS
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "TimeInForce",
    "ExecutionReport",
    "ExecutionType",
    "OrderManager",
    "SmartOrderRouter",
    "create_order_manager",
    "create_smart_router",
    
    # Backtest
    "BacktestConfig",
    "BacktestMode",
    "DataFrequency",
    "DataPortal",
    "Strategy",
    "Portfolio",
    "ExecutionSimulator",
    "EventDrivenBacktester",
    "VectorizedBacktester",
    "WalkForwardOptimizer",
    "BacktestResult",
    "PortfolioState",
    "Trade",
    "create_backtest_config",
    "create_data_portal",
    "create_backtester",
    
    # TCA
    "TCAConfig",
    "SlippageModel",
    "ExecutionMetrics",
    "OrderTCA",
    "MarketImpactModel",
    "TCACalculator",
    "PerformanceAttribution",
    "create_tca_config",
    "create_tca_calculator",
    "create_market_impact_model",
    
    # Paper Trading
    "PaperTradingConfig",
    "PaperTradingMode",
    "PaperAccount",
    "MarketSnapshot",
    "SimulatedMarket",
    "PaperTradingEngine",
    "create_paper_trading_config",
    "create_paper_trading_engine",
]