"""Risk Management Service - VaR, Stress Testing, and Risk Analytics."""

import asyncio
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional, Tuple
from enum import Enum
from typing import TYPE_CHECKING
from scipy import stats
import numpy as np

if TYPE_CHECKING:
    from erin.data_infra.storage.duckdb import DuckDBStorage
    from erin.market_intel.domain.interfaces import Quote

logger = logging.getLogger(__name__)


class VaRMethod(str, Enum):
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"
    MONTE_CARLO = "MONTE_CARLO"
    CORNISH_FISHER = "CORNISH_FISHER"


class StressScenario(str, Enum):
    HISTORICAL_2008 = "HISTORICAL_2008"
    HISTORICAL_2020 = "HISTORICAL_2020"
    HYPOTHETICAL_EQUITY_CRASH = "HYPOTHETICAL_EQUITY_CRASH"
    HYPOTHETICAL_RATE_SHOCK = "HYPOTHETICAL_RATE_SHOCK"
    HYPOTHETICAL_CREDIT_SPREAD = "HYPOTHETICAL_CREDIT_SPREAD"


@dataclass
class VaRResult:
    """VaR calculation result."""
    portfolio_id: str
    method: VaRMethod
    confidence_level: Decimal
    horizon_days: int
    var_value: Decimal
    es_value: Optional[Decimal] = None  # Expected Shortfall
    as_of_date: date = field(default_factory=date.today)
    computation_time_ms: int = 0
    details: Dict = field(default_factory=dict)


@dataclass
class StressTestResult:
    """Stress test result."""
    portfolio_id: str
    scenario: StressScenario
    portfolio_value: Decimal
    stressed_value: Decimal
    pnl: Decimal
    pnl_pct: Decimal
    details: Dict = field(default_factory=dict)
    as_of_date: date = field(default_factory=date.today)


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics."""
    portfolio_id: str
    as_of_date: date
    
    # VaR
    var_95_1d: Optional[Decimal] = None
    var_99_1d: Optional[Decimal] = None
    var_95_10d: Optional[Decimal] = None
    var_99_10d: Optional[Decimal] = None
    
    # Expected Shortfall
    es_95_1d: Optional[Decimal] = None
    es_99_1d: Optional[Decimal] = None
    
    # Portfolio metrics
    portfolio_value: Decimal = Decimal('0')
    volatility_annual: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    
    # Concentration
    hhi: Optional[Decimal] = None
    max_position_pct: Optional[Decimal] = None
    top_10_pct: Optional[Decimal] = None
    
    # Risk factors
    beta: Optional[Decimal] = None
    tracking_error: Optional[Decimal] = None
    var_contribution: Dict[str, Decimal] = field(default_factory=dict)
    
    # Stress tests
    stress_results: Dict[str, Dict] = field(default_factory=dict)


class RiskEngine:
    """Core risk analytics engine."""
    
    def __init__(self, duckdb_storage: 'DuckDBStorage', market_data_service):
        self.duckdb = duckdb_storage
        self.market_data = market_data_service
        self.returns_cache: Dict[str, np.ndarray] = {}
        self._returns_cache_ttl = 300  # 5 minutes
    
    async def calculate_var(
        self,
        portfolio_id: str,
        method: VaRMethod = VaRMethod.HISTORICAL,
        confidence_level: Decimal = Decimal('0.95'),
        horizon_days: int = 1,
        portfolio_value: Optional[Decimal] = None
    ) -> VaRResult:
        """Calculate Value at Risk."""
        start_time = datetime.utcnow()
        
        # Get portfolio positions and historical returns
        returns = await self._get_portfolio_returns(portfolio_id)
        
        if len(returns) < 30:
            raise ValueError("Insufficient historical data for VaR calculation")
        
        portfolio_value = portfolio_value or Decimal('1000000')  # Default 1M
        
        var_value = Decimal('0')
        es_value = None
        details = {}
        
        if method == VaRMethod.HISTORICAL:
            var_value, es_value, details = self._historical_var(
                returns, confidence_level, horizon_days, portfolio_value
            )
        elif method == VaRMethod.PARAMETRIC:
            var_value, es_value, details = self._parametric_var(
                returns, confidence_level, horizon_days, portfolio_value
            )
        elif method == VaRMethod.MONTE_CARLO:
            var_value, es_value, details = self._monte_carlo_var(
                returns, confidence_level, horizon_days, portfolio_value
            )
        elif method == VaRMethod.CORNISH_FISHER:
            var_value, es_value, details = self._cornish_fisher_var(
                returns, confidence_level, horizon_days, portfolio_value
            )
        
        computation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return VaRResult(
            portfolio_id=portfolio_id,
            method=method,
            confidence_level=confidence_level,
            horizon_days=horizon_days,
            var_value=var_value,
            es_value=es_value,
            computation_time_ms=computation_time,
            details=details
        )
    
    def _historical_var(
        self,
        returns: np.ndarray,
        confidence: Decimal,
        horizon: int,
        portfolio_value: Decimal
    ) -> Tuple[Decimal, Decimal, Dict]:
        """Historical VaR using empirical distribution."""
        # Scale returns to horizon
        if horizon > 1:
            # Scale by sqrt(horizon) for i.i.d. returns
            scaled_returns = returns * np.sqrt(horizon)
        else:
            scaled_returns = returns
        
        # Calculate percentile
        alpha = float(1 - confidence)
        var_percentile = np.percentile(scaled_returns, alpha * 100)
        var_value = abs(var_percentile)
        
        # Expected Shortfall (CVaR)
        tail_returns = scaled_returns[scaled_returns <= var_percentile]
        es_value = abs(np.mean(tail_returns)) if len(tail_returns) > 0 else var_value
        
        details = {
            "observations": len(returns),
            "horizon_days": 1,
            "var_percentile": float(alpha * 100),
            "method": "historical"
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _parametric_var(
        self,
        returns: np.ndarray,
        confidence: Decimal,
        horizon: int,
        portfolio_value: Decimal
    ) -> Tuple[Decimal, Decimal, Dict]:
        """Parametric (Delta-Normal) VaR assuming normal distribution."""
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        
        # Scale to horizon
        horizon_mean = mean * horizon
        horizon_std = std * np.sqrt(horizon)
        
        # Z-score for confidence level
        alpha = float(1 - confidence)
        z_score = stats.norm.ppf(alpha)
        
        var_value = abs(portfolio_value * (horizon_mean + z_score * horizon_std))
        es_value = abs(portfolio_value * (horizon_mean + horizon_std * stats.norm.pdf(z_score) / alpha))
        
        details = {
            "mean": float(mean),
            "std": float(std),
            "z_score": float(z_score),
            "method": "parametric"
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _monte_carlo_var(
        self,
        returns: np.ndarray,
        confidence: Decimal,
        horizon: int,
        portfolio_value: Decimal,
        n_simulations: int = 10000
    ) -> Tuple[Decimal, Decimal, Dict]:
        """Monte Carlo VaR using historical returns resampling."""
        n = len(returns)
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        
        # Generate scenarios
        np.random.seed(42)  # For reproducibility
        simulated_returns = np.random.normal(
            mean, std, size=(n_simulations, 1)  # 1-day horizon
        )
        
        if horizon > 1:
            # Compound returns for multi-day
            simulated_cumulative = np.prod(1 + simulated_returns, axis=1) - 1
        else:
            simulated_cumulative = simulated_returns.flatten()
        
        # Calculate VaR and ES
        alpha = float(1 - confidence)
        var_percentile = np.percentile(simulated_cumulative, alpha * 100)
        var_value = abs(var_percentile)
        
        tail = simulated_cumulative[simulated_cumulative <= var_percentile]
        es_value = abs(np.mean(tail)) if len(tail) > 0 else var_value
        
        details = {
            "n_simulations": n_simulations,
            "mean": float(np.mean(returns)),
            "std": float(np.std(returns)),
            "method": "monte_carlo"
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _cornish_fisher_var(
        self,
        returns: np.ndarray,
        confidence: Decimal,
        horizon: int,
        portfolio_value: Decimal
    ) -> Tuple[Decimal, Decimal, Dict]:
        """Cornish-Fisher VaR accounting for skewness and kurtosis."""
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)
        
        # Scale to horizon
        horizon_mean = mean * horizon
        horizon_std = std * np.sqrt(horizon)
        horizon_skew = skew / np.sqrt(horizon)
        horizon_kurt = kurt / horizon
        
        alpha = float(1 - confidence)
        z = stats.norm.ppf(alpha)
        
        # Cornish-Fisher expansion
        z_cf = (z + 
                (z**2 - 1) * horizon_skew / 6 +
                (z**3 - 3*z) * horizon_kurt / 24 -
                (2*z**3 - 5*z) * horizon_skew**2 / 36)
        
        var_value = abs(portfolio_value * (horizon_mean + z_cf * horizon_std))
        
        # ES approximation
        es_value = var_value * 1.1  # Rough approximation
        
        details = {
            "skewness": float(skew),
            "kurtosis": float(kurt),
            "z_cf": float(z_cf),
            "method": "cornish_fisher"
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    async def run_stress_test(
        self,
        portfolio_id: str,
        scenario: StressScenario,
        portfolio_value: Optional[Decimal] = None
    ) -> StressTestResult:
        """Run stress test for a scenario."""
        # Define scenario shocks
        shocks = self._get_scenario_shocks(scenario)
        
        # Get portfolio positions
        positions = await self._get_portfolio_positions(portfolio_id)
        
        # Apply shocks
        stressed_value = Decimal('0')
        total_pnl = Decimal('0')
        
        for position in positions:
            figi = position.figi
            quantity = position.quantity
            current_price = position.current_price or position.avg_cost
            quantity_decimal = Decimal(str(position.quantity))
            price_decimal = Decimal(str(current_price))
            
            # Apply shock
            shock = shocks.get(figi, shocks.get("default", Decimal('0')))
            shocked_price = price_decimal * (Decimal('1') + shock)
            
            position_value = price_decimal * quantity_decimal
            stressed_value = shocked_price * quantity_decimal
            pnl = stressed_value - position_value
            
            total_value += position_value
            total_pnl += pnl
        
        pnl_pct = (total_pnl / total_value * 100) if total_value > 0 else Decimal('0')
        
        return StressTestResult(
            portfolio_id=portfolio_id,
            scenario=scenario,
            portfolio_value=total_value,
            stressed_value=total_value + total_pnl,
            pnl=total_pnl,
            pnl_pct=total_pnl,
            as_of_date=date.today()
        )
    
    def _get_scenario_shocks(self, scenario: StressScenario) -> Dict[str, Decimal]:
        """Get shock parameters for each scenario."""
        scenarios = {
            StressScenario.HISTORICAL_2008: {
                "default": Decimal('-0.45'),  # 45% drop
                "EQUITY": Decimal('-0.50'),
                "FIXED_INCOME": Decimal('-0.05'),
                "COMMODITY": Decimal('-0.30'),
                "FX": Decimal('-0.10'),
                "default": Decimal('-0.40')
            },
            StressScenario.HISTORICAL_2020: {
                "default": Decimal('-0.35'),
                "EQUITY": Decimal('-0.34'),
                "FIXED_INCOME": Decimal('-0.08'),
                "COMMODITY": Decimal('-0.25'),
                "FX": Decimal('-0.05'),
                "default": Decimal('-0.30')
            },
            StressScenario.HYPOTHETICAL_EQUITY_CRASH: {
                "EQUITY": Decimal('-0.30'),
                "FIXED_INCOME": Decimal('-0.05'),
                "COMMODITY": Decimal('-0.20'),
                "FX": Decimal('-0.10'),
                "default": Decimal('-0.25')
            },
            StressScenario.HYPOTHETICAL_RATE_SHOCK: {
                "FIXED_INCOME": Decimal('-0.15'),  # Rates up 200bps
                "EQUITY": Decimal('-0.10'),
                "default": Decimal('-0.10')
            },
            StressScenario.HYPOTHETICAL_CREDIT_SPREAD: {
                "FIXED_INCOME": Decimal('-0.10'),
                "EQUITY": Decimal('-0.05'),
                "default": Decimal('-0.08')
            }
        }
        
        return scenarios.get(scenario, {"default": Decimal('-0.10')})
    
    async def calculate_risk_metrics(self, portfolio_id: str) -> RiskMetrics:
        """Calculate comprehensive risk metrics for a portfolio."""
        # Get portfolio positions
        positions = await self._get_portfolio_positions(portfolio_id)
        
        # Get historical returns
        returns = await self._get_portfolio_returns(portfolio_id)
        
        metrics = RiskMetrics(
            portfolio_id=portfolio_id,
            as_of_date=date.today()
        )
        
        if len(returns) >= 30:
            # Calculate VaR at multiple levels
            metrics.var_95_1d = (await self.calculate_var(
                portfolio_id, VaRMethod.HISTORICAL, Decimal('0.95'), 1
            )).var_value
            
            metrics.var_99_1d = (await self.calculate_var(
                portfolio_id, VaRMethod.HISTORICAL, Decimal('0.99'), 1
            )).var_value
            
            metrics.var_95_10d = (await self.calculate_var(
                portfolio_id, VaRMethod.HISTORICAL, Decimal('0.95'), 10
            )).var_value
            
            # Expected Shortfall
            es_result = await self.calculate_var(
                portfolio_id, VaRMethod.HISTORICAL, Decimal('0.95'), 1
            )
            metrics.es_95_1d = es_result.es_value
            
            # Portfolio metrics
            returns_arr = np.array(returns)
            metrics.volatility_annual = Decimal(str(np.std(returns) * np.sqrt(252)))
            
            # Sharpe ratio (assuming 2% risk-free)
            if np.std(returns) > 0:
                excess_return = np.mean(returns) * 252 - 0.02
                metrics.sharpe_ratio = Decimal(str(excess_return / np.std(returns) * np.sqrt(252)))
            
            # Max drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            metrics.max_drawdown = Decimal(str(abs(np.min(drawdown))))
            
            # Portfolio value and positions
            positions = await self._get_portfolio_positions(portfolio_id)
            total_value = sum(p.market_value or Decimal('0') for p in positions)
            metrics.portfolio_value = total_value
            
            # Concentration
            values = [float(p.market_value or 0) for p in positions if p.market_value]
            if values:
                total = sum(values)
                weights = [v / sum(values) for v in values]
                metrics.hhi = Decimal(str(sum(w**2 for w in weights)))
                metrics.max_position_pct = Decimal(str(max(values) / sum(values) * 100))
        
        return metrics
    
    async def _get_portfolio_returns(self, portfolio_id: str) -> np.ndarray:
        """Get historical portfolio returns."""
        cache_key = f"returns:{portfolio_id}"
        
        if cache_key in self.returns_cache:
            cached, timestamp = self.returns_cache[cache_key]
            if (datetime.utcnow() - timestamp).seconds < self._returns_cache_ttl:
                return cached
        
        # In real implementation, would calculate from historical positions and prices
        # For now, generate synthetic returns
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)  # Daily returns for 1 year
        
        self.returns_cache[cache_key] = (returns, datetime.utcnow())
        return returns
    
    async def _get_portfolio_positions(self, portfolio_id: str) -> List[Any]:
        """Get portfolio positions."""
        # In real implementation, would fetch from storage
        return []


class RiskService:
    """High-level risk management service."""
    
    def __init__(
        self,
        risk_engine: RiskEngine,
        storage: 'SQLiteStorage',
        market_data_service
    ):
        self.engine = risk_engine
        self.storage = storage
        self.market_data = market_data_service
    
    async def get_var(
        self,
        portfolio_id: str,
        method: str = "historical",
        confidence: float = 0.95,
        horizon: int = 1
    ) -> Dict:
        """Get VaR for portfolio."""
        method_enum = VaRMethod[method.upper()]
        confidence = Decimal(str(confidence))
        
        result = await self.engine.calculate_var(
            portfolio_id=portfolio_id,
            method=VaRMethod[method.upper()],
            confidence_level=Decimal(str(confidence)),
            horizon_days=horizon
        )
        
        return {
            "portfolio_id": result.portfolio_id,
            "method": result.method.value,
            "confidence_level": float(result.confidence_level),
            "horizon_days": result.horizon_days,
            "var_value": float(result.var_value),
            "es_value": float(result.es_value) if result.es_value else None,
            "computation_time_ms": result.computation_time_ms,
            "details": result.details
        }
    
    async def run_stress_test(
        self,
        portfolio_id: str,
        scenario: str
    ) -> Dict:
        """Run stress test."""
        scenario_enum = StressScenario[scenario.upper()]
        
        result = await self.engine.run_stress_test(
            portfolio_id=portfolio_id,
            scenario=scenario_enum
        )
        
        return {
            "portfolio_id": result.portfolio_id,
            "scenario": result.scenario.value,
            "portfolio_value": float(result.portfolio_value),
            "stressed_value": float(result.stressed_value),
            "pnl": float(result.pnl),
            "pnl_pct": float(result.pnl_pct),
            "as_of_date": result.as_of_date.isoformat()
        }
    
    async def get_risk_metrics(self, portfolio_id: str) -> Dict:
        """Get comprehensive risk metrics."""
        metrics = await self.engine.calculate_risk_metrics(portfolio_id)
        
        return {
            "portfolio_id": metrics.portfolio_id,
            "as_of_date": metrics.as_of_date.isoformat(),
            "var_95_1d": float(metrics.var_95_1d) if metrics.var_95_1d else None,
            "var_99_1d": float(metrics.var_99_1d) if metrics.var_99_1d else None,
            "var_95_10d": float(metrics.var_95_10d) if metrics.var_95_10d else None,
            "es_95_1d": float(metrics.es_95_1d) if metrics.es_95_1d else None,
            "volatility_annual": float(metrics.volatility_annual) if metrics.volatility_annual else None,
            "sharpe_ratio": float(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
            "max_drawdown": float(metrics.max_drawdown) if metrics.max_drawdown else None,
            "hhi": float(metrics.hhi) if metrics.hhi else None,
            "max_position_pct": float(metrics.max_position_pct) if metrics.max_position_pct else None,
            "portfolio_value": float(metrics.portfolio_value),
            "stress_results": metrics.stress_results
        }