"""Value at Risk Engine - Historical, Parametric, Monte Carlo, and ES methods."""

import numpy as np
import scipy.stats as stats
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime
from typing import TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from erin.market_intel.quant import DistributionEngine, MonteCarloEngine, MCConfig, MonteCarloModel
    from erin.market_intel.quant.optimization import OptimizationEngine


class VaRMethod(str, Enum):
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"           # Delta-Normal
    PARAMETRIC_EWMA = "PARAMETRIC_EWMA" # EWMA volatility
    MONTE_CARLO = "MONTE_CARLO"
    CORNISH_FISHER = "CORNISH_FISHER"
    EXTREME_VALUE = "EXTREME_VALUE"     # EVT/GPD


class ESGMeasure(str, Enum):
    VAR = "VAR"
    ES = "ES"                           # Expected Shortfall / CVaR
    MEDIAN_ES = "MEDIAN_ES"             # Median Shortfall


@dataclass
class VaRConfig:
    """VaR calculation configuration."""
    method: VaRMethod = VaRMethod.HISTORICAL
    confidence_level: Decimal = Decimal('0.95')
    horizon_days: int = 1
    lambda_ewma: Decimal = Decimal('0.94')  # EWMA decay factor
    n_simulations: int = 100000
    distribution_engine = None
    monte_carlo_engine = None
    
    # Historical window
    lookback_days: int = 252
    
    # Parametric options
    use_cornish_fisher: bool = False
    
    # EVT options
    evt_threshold_pct: Decimal = Decimal('0.10')  # Top 10% for GPD fitting


@dataclass
class VaRResult:
    """VaR calculation result."""
    portfolio_id: str
    method: VaRMethod
    confidence_level: Decimal
    horizon_days: int
    var_value: Decimal
    es_value: Optional[Decimal] = None
    var_currency: str = "USD"
    es_currency: str = "USD"
    as_of_date: date = field(default_factory=date.today)
    computation_time_ms: int = 0
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Component VaR
    component_var: Dict[str, Decimal] = field(default_factory=dict)
    marginal_var: Dict[str, Decimal] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'method': self.method.value,
            'confidence_level': float(self.confidence_level),
            'horizon_days': self.horizon_days,
            'var_value': float(self.var_value),
            'es_value': float(self.es_value) if self.es_value else None,
            'var_currency': self.var_currency,
            'es_currency': self.es_currency,
            'as_of_date': self.as_of_date.isoformat(),
            'computation_time_ms': self.computation_time_ms,
            'details': self.details,
            'component_var': {k: float(v) for k, v in self.component_var.items()},
            'marginal_var': {k: float(v) for k, v in self.marginal_var.items()}
        }


@dataclass
class VaRBacktestResult:
    """VaR backtesting result."""
    portfolio_id: str
    method: VaRMethod
    confidence_level: Decimal
    test_period_start: date
    test_period_end: date
    n_observations: int
    n_exceptions: int
    exception_rate: float
    
    # Kupiec POF test
    kupiec_lr_stat: float
    kupiec_p_value: float
    kupiec_reject: bool
    
    # Christoffersen independence test
    christoffersen_lr_stat: float
    christoffersen_p_value: float
    christoffersen_reject: bool
    
    # Basel traffic light
    basel_zone: str  # GREEN, YELLOW, RED
    
    # Exception details
    exception_dates: List[date] = field(default_factory=list)
    exception_magnitudes: List[float] = field(default_factory=list)


class VaREngine:
    """Comprehensive VaR engine with multiple methodologies."""
    
    def __init__(
        self,
        distribution_engine = None,
        monte_carlo_engine = None,
        optimization_engine = None
    ):
        self.dist_engine = distribution_engine
        self.mc_engine = monte_carlo_engine
        self.opt_engine = optimization_engine
    
    def calculate_var(
        self,
        portfolio_returns: np.ndarray,
        portfolio_value: Decimal,
        config: VaRConfig = None
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """Calculate VaR and ES for a portfolio return series."""
        
        if config is None:
            config = VaRConfig()
        
        returns = portfolio_returns
        portfolio_val = float(portfolio_value)
        alpha = float(1 - config.confidence_level)
        
        if len(returns) < 30:
            raise ValueError("Insufficient data for VaR calculation (minimum 30 observations)")
        
        if config.method == VaRMethod.HISTORICAL:
            return self._historical_var(returns, portfolio_val, alpha, config)
        elif config.method == VaRMethod.PARAMETRIC:
            return self._parametric_var(returns, portfolio_val, alpha, config)
        elif config.method == VaRMethod.PARAMETRIC_EWMA:
            return self._ewma_var(returns, portfolio_val, alpha, config)
        elif config.method == VaRMethod.MONTE_CARLO:
            return self._monte_carlo_var(returns, portfolio_val, alpha, config)
        elif config.method == VaRMethod.CORNISH_FISHER:
            return self._cornish_fisher_var(returns, portfolio_val, alpha, config)
        elif config.method == VaRMethod.EXTREME_VALUE:
            return self._evt_var(returns, portfolio_val, alpha, config)
        else:
            raise ValueError(f"Unsupported VaR method: {config.method}")
    
    def _historical_var(
        self,
        returns: np.ndarray,
        portfolio_val: float,
        alpha: float,
        config: VaRConfig
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """Historical VaR using empirical distribution."""
        
        # Scale returns to horizon
        if config.horizon_days > 1:
            # For i.i.d. returns, scale by sqrt(horizon)
            scaled_returns = returns * np.sqrt(config.horizon_days)
        else:
            scaled_returns = returns
        
        # VaR at alpha quantile
        var_percentile = np.percentile(scaled_returns, alpha * 100)
        var_value = abs(var_percentile) * portfolio_val
        
        # Expected Shortfall (average of tail losses)
        tail_returns = scaled_returns[scaled_returns <= var_percentile]
        es_value = abs(np.mean(tail_returns)) * portfolio_val if len(tail_returns) > 0 else var_value
        
        details = {
            'observations': len(returns),
            'horizon_days': config.horizon_days,
            'var_percentile': alpha * 100,
            'var_return': float(var_percentile)
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _parametric_var(
        self,
        returns: np.ndarray,
        portfolio_val: float,
        alpha: float,
        config: VaRConfig
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """Parametric (Delta-Normal) VaR assuming normal distribution."""
        
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        
        # Scale to horizon
        horizon_mean = mean * config.horizon_days
        horizon_std = std * np.sqrt(config.horizon_days)
        
        if config.use_cornish_fisher:
            return self._cornish_fisher_var(returns, portfolio_val, alpha, config)
        
        # Z-score
        z_score = stats.norm.ppf(alpha)
        
        var_value = abs(portfolio_val * (horizon_mean + z_score * horizon_std))
        
        # Expected Shortfall for normal
        es_value = abs(portfolio_val * (horizon_mean + horizon_std * stats.norm.pdf(z_score) / alpha))
        
        details = {
            'mean': float(mean),
            'std': float(std),
            'horizon_mean': float(horizon_mean),
            'horizon_std': float(horizon_std),
            'z_score': float(z_score),
            'assumption': 'normal'
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _ewma_var(
        self,
        returns: np.ndarray,
        portfolio_val: float,
        alpha: float,
        config: VaRConfig
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """EWMA VaR with exponentially weighted volatility."""
        
        lam = float(config.lambda_ewma)
        n = len(returns)
        
        # EWMA variance
        var = np.zeros(n)
        var[0] = np.var(returns)
        
        for t in range(1, n):
            var[t] = lam * var[t-1] + (1 - lam) * returns[t-1]**2
        
        current_vol = np.sqrt(var[-1])
        mean = np.mean(returns)
        
        # Scale to horizon
        horizon_mean = mean * config.horizon_days
        horizon_vol = current_vol * np.sqrt(config.horizon_days)
        
        z_score = stats.norm.ppf(alpha)
        
        var_value = abs(portfolio_val * (horizon_mean + z_score * horizon_vol))
        es_value = abs(portfolio_val * (horizon_mean + horizon_vol * stats.norm.pdf(z_score) / alpha))
        
        details = {
            'ewma_lambda': lam,
            'current_vol': float(current_vol),
            'horizon_vol': float(horizon_vol),
            'z_score': float(z_score)
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _cornish_fisher_var(
        self,
        returns: np.ndarray,
        portfolio_val: float,
        alpha: float,
        config: VaRConfig
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """Cornish-Fisher VaR accounting for skewness and kurtosis."""
        
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)  # Excess kurtosis
        
        # Scale to horizon
        h = config.horizon_days
        horizon_mean = mean * h
        horizon_std = std * np.sqrt(h)
        horizon_skew = skew / np.sqrt(h)
        horizon_kurt = kurt / h
        
        z = stats.norm.ppf(alpha)
        
        # Cornish-Fisher expansion
        z_cf = (z + 
                (z**2 - 1) * horizon_skew / 6 +
                (z**3 - 3*z) * horizon_kurt / 24 -
                (2*z**3 - 5*z) * horizon_skew**2 / 36)
        
        var_value = abs(portfolio_val * (horizon_mean + z_cf * horizon_std))
        
        # ES approximation using Cornish-Fisher
        es_value = var_value * 1.1  # Rough approximation
        
        details = {
            'skewness': float(skew),
            'kurtosis': float(kurt),
            'horizon_skew': float(horizon_skew),
            'horizon_kurt': float(horizon_kurt),
            'z_score': float(z),
            'z_cf': float(z_cf)
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _monte_carlo_var(
        self,
        returns: np.ndarray,
        portfolio_val: float,
        alpha: float,
        config: VaRConfig
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """Monte Carlo VaR using fitted distribution or historical resampling."""
        
        n_sim = config.n_simulations
        
        if self.dist_engine:
            # Fit distribution and simulate
            fit_results = self.dist_engine.fit_multiple(returns)
            best_fit = fit_results[0]
            
            simulated = self.dist_engine.rvs(
                n_sim, best_fit.dist_type, best_fit.params
            )
        else:
            # Historical resampling (bootstrap)
            n = len(returns)
            indices = np.random.randint(0, n, size=(n_sim, config.horizon_days))
            simulated = np.mean(returns[indices], axis=1) * config.horizon_days
        
        # Scale to portfolio value
        simulated_pnl = simulated * portfolio_val
        
        var_percentile = np.percentile(simulated_pnl, alpha * 100)
        var_value = abs(var_percentile)
        
        tail = simulated_pnl[simulated_pnl <= var_percentile]
        es_value = abs(np.mean(tail)) if len(tail) > 0 else var_value
        
        details = {
            'n_simulations': n_sim,
            'method': 'fitted_distribution' if self.dist_engine else 'bootstrap'
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def _evt_var(
        self,
        returns: np.ndarray,
        portfolio_val: float,
        alpha: float,
        config: VaRConfig
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Any]]:
        """Extreme Value Theory VaR using Generalized Pareto Distribution."""
        
        # Focus on left tail (losses)
        losses = -returns  # Positive = losses
        
        # Threshold selection (e.g., 90th percentile)
        threshold_pct = float(config.evt_threshold_pct)
        threshold = np.percentile(losses, (1 - threshold_pct) * 100)
        
        # Exceedances
        exceedances = losses[losses > threshold] - threshold
        
        if len(exceedances) < 20:
            warnings.warn("Insufficient exceedances for EVT, falling back to parametric")
            return self._parametric_var(returns, portfolio_val, alpha, config)
        
        # Fit GPD using MLE
        from scipy.optimize import minimize
        
        def gpd_nll(params):
            xi, beta = params
            if beta <= 0:
                return 1e10
            if xi == 0:
                return -np.sum(-np.log(beta) - exceedances / beta)
            if xi > 0 and np.any(1 + xi * exceedances / beta <= 0):
                return 1e10
            return -np.sum(-np.log(beta) - (1 + 1/xi) * np.log(1 + xi * exceedances / beta))
        
        # Initial guess
        xi_init = 0.1
        beta_init = np.mean(exceedances)
        
        result = minimize(gpd_nll, [xi_init, beta_init], bounds=[(-0.5, 0.5), (1e-6, None)])
        
        if not result.success:
            warnings.warn("GPD fitting failed, falling back to parametric")
            return self._parametric_var(returns, portfolio_val, alpha, config)
        
        xi, beta = result.x
        
        # VaR using GPD
        n = len(returns)
        n_exceed = len(exceedances)
        exceedance_rate = n_exceed / n
        
        # Quantile of GPD
        p = alpha / exceedance_rate
        
        if xi == 0:
            var_loss = threshold + beta * np.log(p)
        else:
            var_loss = threshold + beta * (p**(-xi) - 1) / xi
        
        var_value = var_loss * portfolio_val
        
        # ES for GPD
        if xi < 1:
            es_loss = (var_loss + beta - xi * threshold) / (1 - xi)
        else:
            es_loss = var_loss * 1.1  # Approximation for infinite mean
        
        es_value = es_loss * portfolio_val
        
        details = {
            'threshold': float(threshold),
            'n_exceedances': n_exceed,
            'exceedance_rate': float(exceedance_rate),
            'gpd_xi': float(xi),
            'gpd_beta': float(beta)
        }
        
        return Decimal(str(var_value)), Decimal(str(es_value)), details
    
    def calculate_component_var(
        self,
        returns_matrix: np.ndarray,  # (n_obs, n_assets)
        weights: np.ndarray,
        portfolio_value: Decimal,
        config: VaRConfig = None
    ) -> Tuple[Decimal, Optional[Decimal], Dict[str, Decimal], Dict[str, Decimal]]:
        """Calculate component VaR for each asset."""
        
        if config is None:
            config = VaRConfig()
        
        n_obs, n_assets = returns_matrix.shape
        portfolio_returns = returns_matrix @ weights
        
        # Portfolio VaR
        port_var, port_es, details = self.calculate_var(
            portfolio_returns, portfolio_value, config
        )
        
        # Component VaR using marginal VaR
        component_var = {}
        marginal_var = {}
        
        for i in range(n_assets):
            # Perturb weight
            eps = 1e-4
            weights_perturbed = weights.copy()
            weights_perturbed[i] += eps
            weights_perturbed = weights_perturbed / weights_perturbed.sum()
            
            port_ret_pert = returns_matrix @ weights_perturbed
            var_pert, _, _ = self.calculate_var(port_ret_pert, portfolio_value, config)
            
            mvar = (float(var_pert) - float(port_var)) / eps
            marginal_var[i] = Decimal(str(mvar))
            component_var[i] = Decimal(str(mvar * weights[i]))
        
        return port_var, port_es, component_var, marginal_var
    
    def run_backtest(
        self,
        returns: np.ndarray,
        portfolio_value: Decimal,
        config: VaRConfig = None,
        test_start: int = 252  # Start backtest after 1 year
    ) -> VaRBacktestResult:
        """Run VaR backtest with Kupiec and Christoffersen tests."""
        
        if config is None:
            config = VaRConfig()
        
        n = len(returns)
        if n < test_start + 10:
            raise ValueError("Insufficient data for backtest")
        
        alpha = float(1 - config.confidence_level)
        n_test = n - test_start
        
        exceptions = []
        exception_dates = []
        exception_magnitudes = []
        
        for t in range(test_start, n):
            # Use rolling window
            window_returns = returns[t-test_start:t]
            
            var_val, _, _ = self.calculate_var(window_returns, portfolio_value, config)
            var_return = float(var_val) / float(portfolio_value)
            
            actual_return = returns[t]
            
            if actual_return < -var_return:
                exceptions.append(t)
                exception_dates.append(date.today())  # Would use actual dates
                exception_magnitudes.append(abs(actual_return / var_return))
        
        n_exceptions = len(exceptions)
        exception_rate = n_exceptions / n_test if n_test > 0 else 0
        
        # Kupiec POF test
        expected_exceptions = n_test * alpha
        
        if n_exceptions > 0 and n_exceptions < n_test:
            kupiec_lr = -2 * (
                n_exceptions * np.log(alpha) + 
                (n_test - n_exceptions) * np.log(1 - alpha) -
                n_exceptions * np.log(exception_rate) - 
                (n_test - n_exceptions) * np.log(1 - exception_rate)
            )
            kupiec_p = 1 - stats.chi2.cdf(kupiec_lr, 1)
        else:
            kupiec_lr = 0
            kupiec_p = 1.0
        
        kupiec_reject = kupiec_p < 0.05
        
        # Christoffersen independence test
        if len(exceptions) >= 2:
            # Test if exceptions cluster
            exception_indicator = np.zeros(n_test)
            exception_indicator[np.array(exceptions) - test_start] = 1
            
            n_00 = np.sum((exception_indicator[:-1] == 0) & (exception_indicator[1:] == 0))
            n_01 = np.sum((exception_indicator[:-1] == 0) & (exception_indicator[1:] == 1))
            n_10 = np.sum((exception_indicator[:-1] == 1) & (exception_indicator[1:] == 0))
            n_11 = np.sum((exception_indicator[:-1] == 1) & (exception_indicator[1:] == 1))
            
            p01 = n_01 / (n_00 + n_01) if (n_00 + n_01) > 0 else 0
            p11 = n_11 / (n_10 + n_11) if (n_10 + n_11) > 0 else 0
            p = (n_01 + n_11) / (n_test - 1)
            
            if p > 0 and p < 1:
                lr_unrestricted = (n_01 * np.log(p01) + n_00 * np.log(1-p01) + 
                                  n_11 * np.log(p11) + n_10 * np.log(1-p11))
                lr_restricted = (n_01 + n_11) * np.log(p) + (n_00 + n_10) * np.log(1-p)
                christoffersen_lr = -2 * (lr_restricted - lr_unrestricted)
                christoffersen_p = 1 - stats.chi2.cdf(christoffersen_lr, 1)
            else:
                christoffersen_lr = 0
                christoffersen_p = 1.0
        else:
            christoffersen_lr = 0
            christoffersen_p = 1.0
        
        christoffersen_reject = christoffersen_p < 0.05
        
        # Basel traffic light
        if n_exceptions <= expected_exceptions * 1.5:
            basel_zone = "GREEN"
        elif n_exceptions <= expected_exceptions * 2:
            basel_zone = "YELLOW"
        else:
            basel_zone = "RED"
        
        return VaRBacktestResult(
            portfolio_id="portfolio",
            method=config.method,
            confidence_level=config.confidence_level,
            test_period_start=date.today(),
            test_period_end=date.today(),
            n_observations=n_test,
            n_exceptions=n_exceptions,
            exception_rate=exception_rate,
            kupiec_lr_stat=float(kupiec_lr),
            kupiec_p_value=float(kupiec_p),
            kupiec_reject=kupiec_reject,
            christoffersen_lr_stat=float(christoffersen_lr),
            christoffersen_p_value=float(christoffersen_p),
            christoffersen_reject=christoffersen_reject,
            basel_zone=basel_zone,
            exception_dates=exception_dates,
            exception_magnitudes=exception_magnitudes
        )


class StressTestingEngine:
    """Portfolio stress testing with historical and hypothetical scenarios."""
    
    def __init__(self):
        self._scenarios = self._load_default_scenarios()
    
    def _load_default_scenarios(self) -> Dict[str, Dict[str, Decimal]]:
        """Load predefined stress scenarios."""
        return {
            "2008_FINANCIAL_CRISIS": {
                "EQUITY": Decimal("-0.50"),
                "FIXED_INCOME": Decimal("-0.05"),
                "COMMODITY": Decimal("-0.30"),
                "FX": Decimal("-0.10"),
                "REAL_ESTATE": Decimal("-0.40"),
                "DEFAULT": Decimal("-0.35")
            },
            "2020_COVID_CRASH": {
                "EQUITY": Decimal("-0.34"),
                "FIXED_INCOME": Decimal("-0.08"),
                "COMMODITY": Decimal("-0.25"),
                "FX": Decimal("-0.05"),
                "REAL_ESTATE": Decimal("-0.15"),
                "DEFAULT": Decimal("-0.25")
            },
            "1987_BLACK_MONDAY": {
                "EQUITY": Decimal("-0.22"),
                "FIXED_INCOME": Decimal("0.02"),
                "COMMODITY": Decimal("-0.10"),
                "FX": Decimal("-0.05"),
                "DEFAULT": Decimal("-0.15")
            },
            "2011_EUROPEAN_DEBT": {
                "EQUITY": Decimal("-0.20"),
                "FIXED_INCOME": Decimal("-0.10"),
                "FX": Decimal("-0.10"),
                "DEFAULT": Decimal("-0.12")
            },
            "HYPOTHETICAL_EQUITY_CRASH": {
                "EQUITY": Decimal("-0.30"),
                "FIXED_INCOME": Decimal("-0.05"),
                "COMMODITY": Decimal("-0.20"),
                "FX": Decimal("-0.10"),
                "DEFAULT": Decimal("-0.20")
            },
            "HYPOTHETICAL_RATE_SHOCK": {
                "FIXED_INCOME": Decimal("-0.15"),
                "EQUITY": Decimal("-0.10"),
                "COMMODITY": Decimal("-0.05"),
                "DEFAULT": Decimal("-0.08")
            },
            "HYPOTHETICAL_CREDIT_SPREAD": {
                "FIXED_INCOME": Decimal("-0.10"),
                "EQUITY": Decimal("-0.05"),
                "DEFAULT": Decimal("-0.07")
            },
            "HYPOTHETICAL_INFLATION_SPIKE": {
                "COMMODITY": Decimal("0.20"),
                "FIXED_INCOME": Decimal("-0.12"),
                "EQUITY": Decimal("-0.08"),
                "REAL_ESTATE": Decimal("0.05"),
                "DEFAULT": Decimal("-0.05")
            },
        }
    
    def add_scenario(self, name: str, shocks: Dict[str, Decimal]):
        """Add custom stress scenario."""
        self._scenarios[name] = shocks
    
    def run_stress_test(
        self,
        portfolio_returns: Dict[str, np.ndarray],  # asset -> returns
        portfolio_weights: Dict[str, float],
        scenario_name: str,
        portfolio_value: Decimal
    ) -> Dict[str, Any]:
        """Run stress test for a scenario."""
        
        if scenario_name not in self._scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        shocks = self._scenarios[scenario_name]
        
        # Calculate portfolio return under stress
        stressed_return = 0.0
        
        for asset, weight in portfolio_weights.items():
            asset_returns = portfolio_returns.get(asset)
            if asset_returns is None or len(asset_returns) == 0:
                continue
            
            # Get asset class (simplified)
            # In practice, would map asset to asset class
            shock = shocks.get("DEFAULT", Decimal("0"))
            
            asset_return = weight * float(shock)
            stressed_return += asset_return
        
        stressed_value = portfolio_value * (Decimal("1") + Decimal(str(stressed_return)))
        pnl = stressed_value - portfolio_value
        pnl_pct = (pnl / portfolio_value) * Decimal("100")
        
        return {
            "scenario": scenario_name,
            "portfolio_value": float(portfolio_value),
            "stressed_value": float(stressed_value),
            "pnl": float(pnl),
            "pnl_pct": float(pnl_pct),
            "stressed_return": stressed_return,
            "shocks_applied": {k: float(v) for k, v in shocks.items()}
        }
    
    def run_all_scenarios(
        self,
        portfolio_returns: Dict[str, np.ndarray],
        portfolio_weights: Dict[str, float],
        portfolio_value: Decimal
    ) -> Dict[str, Any]:
        """Run all predefined stress scenarios."""
        
        results = {}
        for scenario_name in self._scenarios:
            results[scenario_name] = self.run_stress_test(
                portfolio_returns, portfolio_weights, scenario_name, portfolio_value
            )
        
        # Summary
        pnls = [r["pnl"] for r in results.values()]
        worst = min(pnls) if pnls else 0
        best = max(pnls) if pnls else 0
        
        return {
            "scenarios": results,
            "summary": {
                "worst_case_pnl": worst,
                "best_case_pnl": best,
                "average_pnl": np.mean(pnls) if pnls else 0
            }
        }


def create_var_engine(
    distribution_engine = None,
    monte_carlo_engine = None,
    optimization_engine = None
) -> VaREngine:
    """Create VaR engine instance."""
    return VaREngine(distribution_engine, monte_carlo_engine, optimization_engine)


def create_stress_testing_engine() -> StressTestingEngine:
    """Create stress testing engine instance."""
    return StressTestingEngine()