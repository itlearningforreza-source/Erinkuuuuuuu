"""Optimization Engine - Portfolio optimization with multiple objectives."""

import numpy as np
import scipy.optimize as optimize
import scipy.linalg as linalg
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings

from erin.market_intel.quant.factor_models import FactorModelEngine, RiskDecomposition


class OptimizationMethod(str, Enum):
    MEAN_VARIANCE = "MEAN_VARIANCE"
    MIN_VARIANCE = "MIN_VARIANCE"
    MAX_SHARPE = "MAX_SHARPE"
    MAX_RETURN = "MAX_RETURN"
    RISK_PARITY = "RISK_PARITY"
    HRP = "HRP"                    # Hierarchical Risk Parity
    BLACK_LITTERMAN = "BLACK_LITTERMAN"
    MAX_DIVERSIFICATION = "MAX_DIVERSIFICATION"
    MIN_CVAR = "MIN_CVAR"          # Conditional VaR
    MAX_UTILITY = "MAX_UTILITY"


class RiskMeasure(str, Enum):
    VARIANCE = "VARIANCE"
    CVAR = "CVAR"                  # Conditional Value at Risk
    DRAWDOWN = "DRAWDOWN"
    SEMI_VARIANCE = "SEMI_VARIANCE"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"


@dataclass
class OptimizationConfig:
    """Portfolio optimization configuration."""
    method: OptimizationMethod = OptimizationMethod.MEAN_VARIANCE
    risk_measure: RiskMeasure = RiskMeasure.VARIANCE
    
    # Constraints
    weight_min: float = 0.0
    weight_max: float = 1.0
    sum_weights: float = 1.0
    max_turnover: Optional[float] = None
    max_concentration: Optional[float] = None
    
    # Risk parameters
    target_return: Optional[float] = None
    target_risk: Optional[float] = None
    risk_aversion: float = 1.0
    
    # Transaction costs
    transaction_cost_bps: float = 0.0
    current_weights: Optional[Dict[str, float]] = None
    
    # Factor model
    use_factor_model: bool = False
    factor_model_config: Optional[Dict] = None
    
    # Black-Litterman
    market_caps: Optional[Dict[str, float]] = None
    risk_free_rate: float = 0.02
    tau: float = 0.025
    
    # Risk Parity
    risk_budget: Optional[Dict[str, float]] = None
    
    # Solver options
    solver: str = "SLSQP"
    max_iter: int = 1000
    tol: float = 1e-8


@dataclass
class OptimizationResult:
    """Portfolio optimization result."""
    weights: Dict[str, float]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    objective_value: float
    success: bool
    message: str
    iterations: int
    
    # Risk decomposition
    factor_risk: Optional[float] = None
    idiosyncratic_risk: Optional[float] = None
    risk_contributions: Optional[Dict[str, float]] = None
    
    # Constraints satisfaction
    constraint_violations: Dict[str, float] = field(default_factory=dict)
    
    # Additional metrics
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None


class OptimizationEngine:
    """Portfolio optimization engine with multiple methods."""
    
    def __init__(self):
        self._returns = None
        self._cov_matrix = None
        self._factor_engine = None
        self._assets = []
    
    def set_data(
        self,
        returns: np.ndarray,
        assets: List[str],
        cov_matrix: np.ndarray = None,
        factor_engine: FactorModelEngine = None
    ):
        """Set optimization data."""
        self._returns = returns
        self._assets = assets
        self._factor_engine = factor_engine
        
        if cov_matrix is not None:
            self._cov_matrix = cov_matrix
        else:
            self._cov_matrix = np.cov(returns, rowvar=False)
    
    def _prepare_constraints(
        self,
        config: OptimizationConfig,
        n_assets: int
    ) -> List[Dict]:
        """Prepare optimization constraints."""
        
        constraints = []
        
        # Sum of weights constraint
        if config.sum_weights > 0:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: np.sum(w) - config.sum_weights
            })
        
        # Target return constraint
        if config.target_return is not None and self._returns is not None:
            mu = np.mean(self._returns, axis=1) * 252  # Annualize
            constraints.append({
                'type': 'eq',
                'fun': lambda w: w @ mu - config.target_return
            })
        
        # Target risk constraint
        if config.target_risk is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: np.sqrt(w @ self._cov_matrix @ w) - config.target_risk
            })
        
        # Max concentration constraint
        if config.max_concentration is not None:
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: config.max_concentration - np.max(w)
            })
        
        # Turnover constraint
        if config.max_turnover is not None and config.current_weights is not None:
            current = np.array([config.current_weights.get(a, 0) for a in self._assets])
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: config.max_turnover - np.sum(np.abs(w - current))
            })
        
        return constraints
    
    def _prepare_bounds(
        self,
        config: OptimizationConfig,
        n_assets: int
    ) -> List[Tuple[float, float]]:
        """Prepare weight bounds."""
        return [(config.weight_min, config.weight_max)] * n_assets
    
    def _mean_variance_objective(
        self,
        w: np.ndarray,
        mu: np.ndarray,
        risk_aversion: float,
        transaction_cost: float = 0,
        current_weights: np.ndarray = None
    ) -> float:
        """Mean-variance utility function."""
        port_return = w @ mu
        port_risk = w @ self._cov_matrix @ w
        
        # Transaction costs
        tc = 0
        if transaction_cost > 0 and current_weights is not None:
            tc = transaction_cost * np.sum(np.abs(w - current_weights))
        
        return -(port_return - 0.5 * risk_aversion * port_risk - tc)
    
    def _min_variance_objective(self, w: np.ndarray) -> float:
        """Minimum variance objective."""
        return w @ self._cov_matrix @ w
    
    def _max_sharpe_objective(
        self,
        w: np.ndarray,
        mu: np.ndarray,
        risk_free: float
    ) -> float:
        """Negative Sharpe ratio (for minimization)."""
        port_return = w @ mu
        port_risk = np.sqrt(w @ self._cov_matrix @ w)
        if port_risk == 0:
            return 1e10
        return -(port_return - risk_free) / port_risk
    
    def _max_return_objective(
        self,
        w: np.ndarray,
        mu: np.ndarray
    ) -> float:
        """Negative expected return."""
        return -w @ mu
    
    def _risk_parity_objective(
        self,
        w: np.ndarray,
        risk_budget: np.ndarray = None
    ) -> float:
        """Risk parity objective (sum of squared deviations from risk budget)."""
        port_risk = w @ self._cov_matrix @ w
        mrc = self._cov_matrix @ w / port_risk  # Marginal risk contributions
        trc = w * mrc  # Total risk contributions
        
        if risk_budget is None:
            risk_budget = np.ones(len(w)) / len(w)
        
        return np.sum((trc - risk_budget * port_risk)**2)
    
    def _hrp_objective(self, w: np.ndarray) -> float:
        """HRP doesn't use traditional objective - uses clustering."""
        # This is handled separately
        return 0
    
    def _black_litterman_objective(
        self,
        w: np.ndarray,
        bl_mu: np.ndarray,
        risk_aversion: float
    ) -> float:
        """Black-Litterman utility."""
        port_return = w @ bl_mu
        port_risk = w @ self._cov_matrix @ w
        return -(port_return - 0.5 * risk_aversion * port_risk)
    
    def _max_diversification_objective(self, w: np.ndarray) -> float:
        """Maximum diversification ratio (negative for minimization)."""
        # Diversification ratio = weighted avg vol / portfolio vol
        asset_vols = np.sqrt(np.diag(self._cov_matrix))
        port_vol = np.sqrt(w @ self._cov_matrix @ w)
        if port_vol == 0:
            return 1e10
        weighted_avg_vol = w @ asset_vols
        return -weighted_avg_vol / port_vol
    
    def _cvar_objective(
        self,
        w: np.ndarray,
        returns: np.ndarray,
        alpha: float = 0.05
    ) -> float:
        """Conditional Value at Risk objective."""
        portfolio_returns = returns @ w
        var = -np.percentile(portfolio_returns, alpha * 100)
        cvar = -np.mean(portfolio_returns[portfolio_returns <= -var])
        return cvar
    
    def optimize(self, config: OptimizationConfig) -> OptimizationResult:
        """Run portfolio optimization."""
        
        n_assets = len(self._assets)
        mu = np.mean(self._returns, axis=0) * 252  # Annualized returns per asset
        
        # Prepare constraints and bounds
        constraints = self._prepare_constraints(config, n_assets)
        bounds = self._prepare_bounds(config, n_assets)
        
        # Current weights array
        current_w = None
        if config.current_weights:
            current_w = np.array([config.current_weights.get(a, 0) for a in self._assets])
        
        # Transaction cost
        tc = config.transaction_cost_bps / 10000.0  # Convert bps to decimal
        
        # Select objective function
        if config.method == OptimizationMethod.MEAN_VARIANCE:
            objective = lambda w: self._mean_variance_objective(
                w, mu, config.risk_aversion, tc, current_w
            )
        elif config.method == OptimizationMethod.MIN_VARIANCE:
            objective = self._min_variance_objective
        elif config.method == OptimizationMethod.MAX_SHARPE:
            objective = lambda w: self._max_sharpe_objective(w, mu, config.risk_free_rate)
        elif config.method == OptimizationMethod.MAX_RETURN:
            objective = lambda w: self._max_return_objective(w, mu)
        elif config.method == OptimizationMethod.RISK_PARITY:
            risk_budget = None
            if config.risk_budget:
                risk_budget = np.array([config.risk_budget.get(a, 1/n_assets) for a in self._assets])
            objective = lambda w: self._risk_parity_objective(w, risk_budget)
        elif config.method == OptimizationMethod.MAX_DIVERSIFICATION:
            objective = self._max_diversification_objective
        elif config.method == OptimizationMethod.MIN_CVAR:
            if self._returns is None:
                raise ValueError("Returns data required for CVaR optimization")
            objective = lambda w: self._cvar_objective(w, self._returns.T, alpha=0.05)
        elif config.method == OptimizationMethod.BLACK_LITTERMAN:
            # Black-Litterman handled separately
            return self._optimize_black_litterman(config)
        else:
            raise ValueError(f"Unsupported method: {config.method}")
        
        # Initial guess
        if config.current_weights:
            x0 = np.array([config.current_weights.get(a, 1/n_assets) for a in self._assets])
        else:
            x0 = np.ones(n_assets) / n_assets
        
        # Run optimization
        result = optimize.minimize(
            objective,
            x0,
            method=config.solver,
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': config.max_iter, 'ftol': config.tol}
        )
        
        # Extract results
        weights = {self._assets[i]: float(result.x[i]) for i in range(n_assets)}
        
        # Calculate metrics
        port_return = float(result.x @ mu)
        port_risk = float(np.sqrt(result.x @ self._cov_matrix @ result.x))
        sharpe = (port_return - config.risk_free_rate) / port_risk if port_risk > 0 else 0
        
        return OptimizationResult(
            weights=weights,
            expected_return=port_return,
            expected_risk=port_risk,
            sharpe_ratio=sharpe,
            objective_value=-result.fun if config.method in [OptimizationMethod.MAX_SHARPE, OptimizationMethod.MAX_RETURN] else result.fun,
            success=result.success,
            message=result.message,
            iterations=result.nit if hasattr(result, 'nit') else 0
        )
    
    def _optimize_black_litterman(self, config: OptimizationConfig) -> OptimizationResult:
        """Black-Litterman optimization."""
        
        if config.market_caps is None:
            raise ValueError("Market caps required for Black-Litterman")
        
        # Market implied returns (reverse optimization)
        market_weights = np.array([config.market_caps.get(a, 0) for a in self._assets])
        market_weights = market_weights / np.sum(market_weights)
        
        # Implied equilibrium returns
        pi = config.risk_aversion * self._cov_matrix @ market_weights
        
        # If views provided, adjust (simplified - full implementation needs view matrix)
        # For now, use equilibrium returns
        bl_mu = pi
        
        # Optimize with Black-Litterman returns
        objective = lambda w: self._black_litterman_objective(w, bl_mu, config.risk_aversion)
        
        constraints = self._prepare_constraints(config, len(self._assets))
        bounds = self._prepare_bounds(config, len(self._assets))
        
        x0 = market_weights
        result = optimize.minimize(
            objective, x0, method=config.solver,
            bounds=bounds, constraints=constraints,
            options={'maxiter': config.max_iter}
        )
        
        weights = {self._assets[i]: float(result.x[i]) for i in range(len(self._assets))}
        port_return = float(result.x @ mu)
        port_risk = float(np.sqrt(result.x @ self._cov_matrix @ result.x))
        
        return OptimizationResult(
            weights=weights,
            expected_return=port_return,
            expected_risk=port_risk,
            sharpe_ratio=(port_return - config.risk_free_rate) / port_risk if port_risk > 0 else 0,
            objective_value=-result.fun,
            success=result.success,
            message=result.message,
            iterations=result.nit if hasattr(result, 'nit') else 0
        )
    
    def optimize_hrp(self, config: OptimizationConfig = None) -> OptimizationResult:
        """Hierarchical Risk Parity optimization."""
        
        if config is None:
            config = OptimizationConfig()
        
        # Correlation matrix
        corr = self._cov_matrix / np.outer(
            np.sqrt(np.diag(self._cov_matrix)),
            np.sqrt(np.diag(self._cov_matrix))
        )
        
        # Hierarchical clustering
        from scipy.cluster.hierarchy import linkage, dendrogram
        from scipy.spatial.distance import squareform
        
        # Distance matrix
        dist = np.sqrt(0.5 * (1 - corr))
        np.fill_diagonal(dist, 0)
        
        # Hierarchical clustering
        linkage_matrix = linkage(squareform(dist), method='ward')
        
        # Get cluster order
        from scipy.cluster.hierarchy import leaves_list
        ordered_indices = leaves_list(linkage_matrix)
        
        # Recursive bisection
        def get_hrp_weights(indices):
            if len(indices) == 1:
                return np.ones(1)
            
            # Split
            mid = len(indices) // 2
            left = indices[:mid]
            right = indices[mid:]
            
            # Get sub-covariances
            cov_left = self._cov_matrix[np.ix_(left, left)]
            cov_right = self._cov_matrix[np.ix_(right, right)]
            
            # Recursive weights
            w_left = get_hrp_weights(left)
            w_right = get_hrp_weights(right)
            
            # Variance of each cluster
            var_left = w_left @ cov_left @ w_left
            var_right = w_right @ cov_right @ w_right
            
            # Allocate inversely proportional to variance
            total_var = var_left + var_right
            alpha = 1 - var_left / total_var
            
            w = np.zeros(len(indices))
            w[:len(left)] = alpha * w_left
            w[len(left):] = (1 - alpha) * w_right
            
            return w
        
        hrp_weights = get_hrp_weights(ordered_indices)
        
        # Map back to original order
        final_weights = np.zeros(len(self._assets))
        final_weights[ordered_indices] = hrp_weights
        
        # Normalize
        final_weights = final_weights / np.sum(final_weights)
        
        # Metrics
        mu = np.mean(self._returns, axis=1) * 252
        port_return = float(final_weights @ mu)
        port_risk = float(np.sqrt(final_weights @ self._cov_matrix @ final_weights))
        
        return OptimizationResult(
            weights={self._assets[i]: float(final_weights[i]) for i in range(len(self._assets))},
            expected_return=port_return,
            expected_risk=port_risk,
            sharpe_ratio=(port_return - 0.02) / port_risk if port_risk > 0 else 0,
            objective_value=0,
            success=True,
            message="HRP completed",
            iterations=0
        )
    
    def optimize_multiple(
        self,
        configs: List[OptimizationConfig]
    ) -> List[OptimizationResult]:
        """Run multiple optimizations."""
        return [self.optimize(config) for config in configs]
    
    def efficient_frontier(
        self,
        n_points: int = 50,
        risk_free: float = 0.02
    ) -> List[OptimizationResult]:
        """Generate efficient frontier."""
        
        # Min and max return
        mu = np.mean(self._returns, axis=1) * 252
        min_ret = np.min(mu)
        max_ret = np.max(mu)
        
        target_returns = np.linspace(min_ret, max_ret, n_points)
        
        results = []
        for target in target_returns:
            config = OptimizationConfig(
                method=OptimizationMethod.MEAN_VARIANCE,
                target_return=target,
                risk_free_rate=risk_free
            )
            result = self.optimize(config)
            if result.success:
                results.append(result)
        
        return results
    
    def get_risk_contributions(
        self,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Get risk contributions for given weights."""
        
        w = np.array([weights.get(a, 0) for a in self._assets])
        port_risk = np.sqrt(w @ self._cov_matrix @ w)
        
        if port_risk == 0:
            return {a: 0 for a in self._assets}
        
        mrc = self._cov_matrix @ w / port_risk
        trc = w * mrc
        
        return {self._assets[i]: float(trc[i]) for i in range(len(self._assets))}
    
    def get_marginal_risk_contributions(
        self,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Get marginal risk contributions."""
        
        w = np.array([weights.get(a, 0) for a in self._assets])
        port_risk = np.sqrt(w @ self._cov_matrix @ w)
        
        if port_risk == 0:
            return {a: 0 for a in self._assets}
        
        mrc = self._cov_matrix @ w / port_risk
        
        return {self._assets[i]: float(mrc[i]) for i in range(len(self._assets))}
    
    def get_component_contributions(
        self,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Get component contributions to risk (w_i * MRC_i)."""
        
        w = np.array([weights.get(a, 0) for a in self._assets])
        port_risk = np.sqrt(w @ self._cov_matrix @ w)
        
        if port_risk == 0:
            return {a: 0 for a in self._assets}
        
        mrc = self._cov_matrix @ w / port_risk
        ccr = w * mrc
        
        return {self._assets[i]: float(ccr[i]) for i in range(len(self._assets))}


class RebalancingOptimizer:
    """Portfolio rebalancing with transaction costs and constraints."""
    
    def __init__(self, optimization_engine: OptimizationEngine):
        self.engine = optimization_engine
    
    def rebalance(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        max_turnover: float = 0.2,
        transaction_cost_bps: float = 10,
        allow_short: bool = False
    ) -> Dict[str, float]:
        """Rebalance portfolio with constraints."""
        
        config = OptimizationConfig(
            method=OptimizationMethod.MEAN_VARIANCE,
            current_weights=current_weights,
            max_turnover=max_turnover,
            transaction_cost_bps=transaction_cost_bps,
            weight_min=-1.0 if allow_short else 0.0
        )
        
        # Simple rebalancing: minimize distance to target with constraints
        current = np.array([current_weights.get(a, 0) for a in self.engine._assets])
        target = np.array([target_weights.get(a, 0) for a in self.engine._assets])
        
        n = len(self.engine._assets)
        
        def objective(w):
            return np.sum((w - target)**2)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'ineq', 'fun': lambda w: max_turnover - np.sum(np.abs(w - current))}
        ]
        
        bounds = [(0, 1) for _ in range(n)]
        
        result = optimize.minimize(
            objective, current,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        return {self.engine._assets[i]: float(result.x[i]) for i in range(n)}


def create_optimization_engine() -> OptimizationEngine:
    """Create optimization engine instance."""
    return OptimizationEngine()

def create_rebalancing_optimizer(engine: OptimizationEngine) -> RebalancingOptimizer:
    """Create rebalancing optimizer."""
    return RebalancingOptimizer(engine)