"""Monte Carlo Engine - Path simulation for quantitative finance."""

import numpy as np
import scipy.stats as stats
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

from erin.market_intel.quant.distributions import DistributionEngine, DistributionType, create_distribution_engine


class MonteCarloModel(str, Enum):
    GBM = "GBM"                    # Geometric Brownian Motion
    GBM_JUMP = "GBM_JUMP"          # GBM with jumps (Merton)
    HESTON = "HESTON"              # Heston stochastic volatility
    HESTON_JUMP = "HESTON_JUMP"    # Heston with jumps
    BATES = "BATES"                # Bates model (Heston + jumps)
    CIR = "CIR"                    # Cox-Ingersoll-Ross (interest rates)
    VASICEK = "VASICEK"            # Vasicek (interest rates)
    CIR_PLUS = "CIR_PLUS"          # CIR++ (shifted CIR)
    SABR = "SABR"                  # SABR stochastic volatility
    LOCAL_VOL = "LOCAL_VOL"        # Local volatility (Dupire)


class QuasiRandomType(str, Enum):
    PSEUDO = "PSEUDO"              # Standard pseudo-random
    SOBOL = "SOBOL"                # Sobol sequence
    HALTON = "HALTON"              # Halton sequence
    FAURE = "FAURE"                # Faure sequence


@dataclass
class MCConfig:
    """Monte Carlo configuration."""
    model: MonteCarloModel = MonteCarloModel.GBM
    n_paths: int = 10000
    n_steps: int = 252
    time_horizon: float = 1.0  # Years
    seed: Optional[int] = None
    quasi_random: QuasiRandomType = QuasiRandomType.PSEUDO
    antithetic: bool = True
    control_variate: bool = False
    
    # Model-specific parameters
    params: Dict[str, float] = field(default_factory=dict)


@dataclass
class MCResult:
    """Monte Carlo simulation result."""
    paths: np.ndarray  # Shape: (n_paths, n_steps+1) or (n_paths, n_steps+1, n_assets)
    times: np.ndarray  # Time grid
    stats: Dict[str, Any]  # Summary statistics
    config: MCConfig
    runtime_seconds: float


class MonteCarloEngine:
    """Monte Carlo path simulation engine."""
    
    def __init__(self, distribution_engine: DistributionEngine = None):
        self.dist_engine = distribution_engine or create_distribution_engine()
    
    def _generate_random_numbers(
        self,
        n_paths: int,
        n_steps: int,
        n_dims: int,
        quasi_random: QuasiRandomType = QuasiRandomType.PSEUDO,
        antithetic: bool = True,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """Generate random numbers for simulation."""
        
        if seed is not None:
            np.random.seed(seed)
        
        if quasi_random == QuasiRandomType.SOBOL:
            # Use Sobol sequences
            try:
                from scipy.stats import qmc
                sampler = qmc.Sobol(d=n_dims * n_steps, scramble=True, seed=seed)
                samples = sampler.random(n_paths)
                # Reshape
                return samples.reshape(n_paths, n_steps, n_dims)
            except ImportError:
                pass  # Fall back to pseudo-random
        
        # Standard pseudo-random with optional antithetic variates
        if antithetic:
            n_half = (n_paths + 1) // 2
            Z = np.random.randn(n_half, n_steps, n_dims)
            Z_antithetic = -Z
            Z_full = np.vstack([Z, Z_antithetic])[:n_paths]
            return Z_full
        else:
            return np.random.randn(n_paths, n_steps, n_dims)
    
    def _get_model_params(self, config: MCConfig, defaults: Dict[str, float]) -> Dict[str, float]:
        """Merge config params with defaults."""
        params = defaults.copy()
        params.update(config.params)
        return params
    
    def simulate_gbm(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: float,
        n_steps: int,
        n_paths: int,
        Z: np.ndarray = None,
        antithetic: bool = True,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """Simulate Geometric Brownian Motion paths."""
        
        dt = T / n_steps
        
        if Z is None:
            Z = self._generate_random_numbers(n_paths, n_steps, 1, 
                                             QuasiRandomType.PSEUDO, 
                                             antithetic, seed)
        
        # GBM: dS = mu*S*dt + sigma*S*dW
        # S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt)
        
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        
        for t in range(1, n_steps + 1):
            paths[:, t] = paths[:, t-1] * np.exp(drift + diffusion * Z[:, t-1, 0])
        
        return paths
    
    def simulate_gbm_jump(
        self,
        S0: float,
        mu: float,
        sigma: float,
        lam: float,        # Jump intensity
        mu_j: float,       # Jump mean
        sigma_j: float,    # Jump volatility
        T: float,
        n_steps: int,
        n_paths: int,
        Z: np.ndarray = None,
        Z_j: np.ndarray = None,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """Simulate GBM with Merton jumps."""
        
        dt = T / n_steps
        
        if Z is None:
            Z = self._generate_random_numbers(n_paths, n_steps, 2, 
                                             QuasiRandomType.PSEUDO, True, seed)
        
        if Z_j is None:
            Z_j = np.random.randn(n_paths, n_steps)
        
        # Poisson jumps
        N = np.random.poisson(lam * dt, (n_paths, n_steps))
        J = np.zeros((n_paths, n_steps))
        
        for t in range(n_steps):
            jump_sizes = np.random.normal(mu_j, sigma_j, (n_paths,))
            J[:, t] = np.where(N[:, t] > 0, jump_sizes, 0)
        
        drift = (mu - 0.5 * sigma**2 - lam * (np.exp(mu_j + 0.5*sigma_j**2) - 1)) * dt
        diffusion = sigma * np.sqrt(dt)
        
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        
        for t in range(1, n_steps + 1):
            paths[:, t] = paths[:, t-1] * np.exp(
                drift + diffusion * Z[:, t-1, 0] + J[:, t-1]
            )
        
        return paths
    
    def simulate_heston(
        self,
        S0: float,
        v0: float,
        mu: float,
        kappa: float,      # Mean reversion speed
        theta: float,      # Long-term variance
        xi: float,         # Vol of vol
        rho: float,        # Correlation
        T: float,
        n_steps: int,
        n_paths: int,
        Z: np.ndarray = None,
        seed: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate Heston stochastic volatility model.
        
        Returns:
            (spot_paths, variance_paths)
        """
        
        dt = T / n_steps
        
        if Z is None:
            Z = self._generate_random_numbers(n_paths, n_steps, 2, 
                                             QuasiRandomType.PSEUDO, True, seed)
        
        # Cholesky for correlated Brownian motions
        L = np.array([[1, 0], [rho, np.sqrt(1 - rho**2)]])
        
        paths = np.zeros((n_paths, n_steps + 1))
        variances = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        variances[:, 0] = v0
        
        for t in range(1, n_steps + 1):
            # Correlated increments
            dW = Z[:, t-1, :] @ L.T * np.sqrt(dt)
            dW_S = dW[:, 0]
            dW_v = dW[:, 1]
            
            # Variance process (CIR): dv = kappa*(theta - v)*dt + xi*sqrt(v)*dW_v
            v_prev = np.maximum(variances[:, t-1], 1e-8)
            variances[:, t] = v_prev + kappa * (theta - v_prev) * dt + xi * np.sqrt(v_prev) * dW_v
            variances[:, t] = np.maximum(variances[:, t], 1e-8)
            
            # Spot process: dS/S = mu*dt + sqrt(v)*dW_S
            paths[:, t] = paths[:, t-1] * np.exp(
                (mu - 0.5 * v_prev) * dt + np.sqrt(v_prev) * dW_S
            )
        
        return paths, variances
    
    def simulate_cir(
        self,
        r0: float,
        kappa: float,
        theta: float,
        sigma: float,
        T: float,
        n_steps: int,
        n_paths: int,
        Z: np.ndarray = None,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """Simulate Cox-Ingersoll-Ross (CIR) interest rate model."""
        
        dt = T / n_steps
        
        if Z is None:
            Z = self._generate_random_numbers(n_paths, n_steps, 1, 
                                             QuasiRandomType.PSEUDO, True, seed)
        
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = r0
        
        for t in range(1, n_steps + 1):
            r_prev = np.maximum(paths[:, t-1], 1e-8)
            paths[:, t] = r_prev + kappa * (theta - r_prev) * dt + sigma * np.sqrt(r_prev) * Z[:, t-1, 0] * np.sqrt(dt)
            paths[:, t] = np.maximum(paths[:, t], 1e-8)
        
        return paths
    
    def simulate_vasicek(
        self,
        r0: float,
        kappa: float,
        theta: float,
        sigma: float,
        T: float,
        n_steps: int,
        n_paths: int,
        Z: np.ndarray = None,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """Simulate Vasicek interest rate model."""
        
        dt = T / n_steps
        
        if Z is None:
            Z = self._generate_random_numbers(n_paths, n_steps, 1, 
                                             QuasiRandomType.PSEUDO, True, seed)
        
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = r0
        
        for t in range(1, n_steps + 1):
            paths[:, t] = paths[:, t-1] + kappa * (theta - paths[:, t-1]) * dt + sigma * Z[:, t-1, 0] * np.sqrt(dt)
        
        return paths
    
    def simulate_sabr(
        self,
        F0: float,
        alpha: float,      # Initial volatility
        beta: float,       # Elasticity parameter (0 <= beta <= 1)
        nu: float,         # Vol of vol
        rho: float,        # Correlation
        T: float,
        n_steps: int,
        n_paths: int,
        Z: np.ndarray = None,
        seed: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate SABR stochastic volatility model.
        
        dF = alpha * F^beta * dW1
        dalpha = nu * alpha * dW2
        dW1 * dW2 = rho * dt
        
        Returns:
            (forward_paths, alpha_paths)
        """
        
        dt = T / n_steps
        
        if Z is None:
            Z = self._generate_random_numbers(n_paths, n_steps, 2, 
                                             QuasiRandomType.PSEUDO, True, seed)
        
        L = np.array([[1, 0], [rho, np.sqrt(1 - rho**2)]])
        
        forward_paths = np.zeros((n_paths, n_steps + 1))
        alpha_paths = np.zeros((n_paths, n_steps + 1))
        forward_paths[:, 0] = F0
        alpha_paths[:, 0] = alpha
        
        for t in range(1, n_steps + 1):
            dW = Z[:, t-1, :] @ L.T * np.sqrt(dt)
            dW_F = dW[:, 0]
            dW_alpha = dW[:, 1]
            
            a_prev = alpha_paths[:, t-1]
            F_prev = forward_paths[:, t-1]
            
            # Volatility process
            alpha_paths[:, t] = a_prev + nu * a_prev * dW_alpha * np.sqrt(dt)
            alpha_paths[:, t] = np.maximum(alpha_paths[:, t], 1e-8)
            
            # Forward process
            forward_paths[:, t] = F_prev + a_prev * (F_prev**beta) * dW_F * np.sqrt(dt)
            forward_paths[:, t] = np.maximum(forward_paths[:, t], 1e-8)
        
        return forward_paths, alpha_paths
    
    def run(self, config: MCConfig) -> MCResult:
        """Run Monte Carlo simulation based on config."""
        
        start_time = time.time()
        
        n_steps = config.n_steps
        n_paths = config.n_paths
        T = config.time_horizon
        
        # Generate random numbers
        n_dims = self._get_n_dims(config.model)
        Z = self._generate_random_numbers(
            n_paths, n_steps, n_dims,
            config.quasi_random, config.antithetic, config.seed
        )
        
        if config.model == MonteCarloModel.GBM:
            params = self._get_model_params(config, {'mu': 0.05, 'sigma': 0.2})
            paths = self.simulate_gbm(
                S0=params.get('S0', 100),
                mu=params.get('mu', 0.05),
                sigma=params.get('sigma', 0.2),
                T=T,
                n_steps=n_steps,
                n_paths=n_paths,
                Z=Z,
                antithetic=config.antithetic,
                seed=config.seed
            )
        
        elif config.model == MonteCarloModel.GBM_JUMP:
            params = self._get_model_params(config, {
                'mu': 0.05, 'sigma': 0.2,
                'lam': 0.5, 'mu_j': -0.05, 'sigma_j': 0.1
            })
            paths = self.simulate_gbm_jump(
                S0=params.get('S0', 100),
                mu=params.get('mu', 0.05),
                sigma=params.get('sigma', 0.2),
                lam=params.get('lam', 0.5),
                mu_j=params.get('mu_j', -0.05),
                sigma_j=params.get('sigma_j', 0.1),
                T=T,
                n_steps=n_steps,
                n_paths=n_paths,
                Z=Z,
                seed=config.seed
            )
        
        elif config.model == MonteCarloModel.HESTON:
            params = self._get_model_params(config, {
                'S0': 100, 'v0': 0.04, 'mu': 0.05,
                'kappa': 2.0, 'theta': 0.04, 'xi': 0.3, 'rho': -0.7
            })
            paths, var_paths = self.simulate_heston(
                S0=params.get('S0', 100),
                v0=params.get('v0', 0.04),
                mu=params.get('mu', 0.05),
                kappa=params.get('kappa', 2.0),
                theta=params.get('theta', 0.04),
                xi=params.get('xi', 0.3),
                rho=params.get('rho', -0.7),
                T=T,
                n_steps=n_steps,
                n_paths=n_paths,
                Z=Z,
                seed=config.seed
            )
        
        elif config.model == MonteCarloModel.CIR:
            params = self._get_model_params(config, {
                'r0': 0.05, 'kappa': 1.0, 'theta': 0.05, 'sigma': 0.01
            })
            paths = self.simulate_cir(
                r0=params.get('r0', 0.05),
                kappa=params.get('kappa', 1.0),
                theta=params.get('theta', 0.05),
                sigma=params.get('sigma', 0.01),
                T=T,
                n_steps=n_steps,
                n_paths=n_paths,
                Z=Z,
                seed=config.seed
            )
        
        elif config.model == MonteCarloModel.VASICEK:
            params = self._get_model_params(config, {
                'r0': 0.05, 'kappa': 1.0, 'theta': 0.05, 'sigma': 0.01
            })
            paths = self.simulate_vasicek(
                r0=params.get('r0', 0.05),
                kappa=params.get('kappa', 1.0),
                theta=params.get('theta', 0.05),
                sigma=params.get('sigma', 0.01),
                T=T,
                n_steps=n_steps,
                n_paths=n_paths,
                Z=Z,
                seed=config.seed
            )
        
        elif config.model == MonteCarloModel.SABR:
            params = self._get_model_params(config, {
                'F0': 0.05, 'alpha': 0.2, 'beta': 0.5, 'nu': 0.3, 'rho': -0.2
            })
            paths, alpha_paths = self.simulate_sabr(
                F0=params.get('F0', 0.05),
                alpha=params.get('alpha', 0.2),
                beta=params.get('beta', 0.5),
                nu=params.get('nu', 0.3),
                rho=params.get('rho', -0.2),
                T=T,
                n_steps=n_steps,
                n_paths=n_paths,
                Z=Z,
                seed=config.seed
            )
        
        else:
            raise ValueError(f"Unsupported model: {config.model}")
        
        runtime = time.time() - start_time
        
        # Calculate statistics
        stats = self._calculate_path_stats(paths)
        
        return MCResult(
            paths=paths,
            times=np.linspace(0, T, n_steps + 1),
            stats=stats,
            config=config,
            runtime_seconds=runtime
        )
    
    def _get_n_dims(self, model: MonteCarloModel) -> int:
        """Get number of Brownian motion dimensions for model."""
        dims = {
            MonteCarloModel.GBM: 1,
            MonteCarloModel.GBM_JUMP: 2,
            MonteCarloModel.HESTON: 2,
            MonteCarloModel.HESTON_JUMP: 3,
            MonteCarloModel.BATES: 3,
            MonteCarloModel.CIR: 1,
            MonteCarloModel.VASICEK: 1,
            MonteCarloModel.CIR_PLUS: 1,
            MonteCarloModel.SABR: 2,
            MonteCarloModel.LOCAL_VOL: 1,
        }
        return dims.get(model, 1)
    
    def _calculate_path_stats(self, paths: np.ndarray) -> Dict[str, Any]:
        """Calculate summary statistics for simulated paths."""
        
        if paths.ndim == 2:
            # Single asset
            final_values = paths[:, -1]
            log_returns = np.log(paths[:, 1:] / paths[:, :-1])
        else:
            # Multi-asset - use first asset
            final_values = paths[:, -1, 0]
            log_returns = np.log(paths[:, 1:, 0] / paths[:, :-1, 0])
        
        return {
            'mean_final': float(np.mean(final_values)),
            'std_final': float(np.std(final_values)),
            'min_final': float(np.min(final_values)),
            'max_final': float(np.max(final_values)),
            'percentiles': {
                '1%': float(np.percentile(final_values, 1)),
                '5%': float(np.percentile(final_values, 5)),
                '25%': float(np.percentile(final_values, 25)),
                '50%': float(np.percentile(final_values, 50)),
                '75%': float(np.percentile(final_values, 75)),
                '95%': float(np.percentile(final_values, 95)),
                '99%': float(np.percentile(final_values, 99)),
            },
            'mean_log_return': float(np.mean(log_returns)),
            'std_log_return': float(np.std(log_returns)),
            'skewness': float(stats.skew(final_values)),
            'kurtosis': float(stats.kurtosis(final_values)),
        }
    
    # ============================================================
    # Option Pricing
    # ============================================================
    
    def price_european_option(
        self,
        S0: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = 'call',
        n_paths: int = 100000,
        n_steps: int = 50,
        model: MonteCarloModel = MonteCarloModel.GBM,
        **model_params
    ) -> Dict[str, float]:
        """Price European option using Monte Carlo."""
        
        config = MCConfig(
            model=model,
            n_paths=n_paths,
            n_steps=n_steps,
            time_horizon=T,
            params={
                'S0': S0,
                'mu': r,  # Risk-neutral drift
                'sigma': sigma,
                **model_params
            }
        )
        
        result = self.run(config)
        final_spots = result.paths[:, -1]
        
        if option_type.lower() == 'call':
            payoffs = np.maximum(final_spots - K, 0)
        else:
            payoffs = np.maximum(K - final_spots, 0)
        
        # Discount
        price = np.exp(-r * T) * np.mean(payoffs)
        stderr = np.exp(-r * T) * np.std(payoffs) / np.sqrt(n_paths)
        
        return {
            'price': float(price),
            'std_error': float(stderr),
            'ci_lower': float(price - 1.96 * stderr),
            'ci_upper': float(price + 1.96 * stderr),
            'runtime': result.runtime_seconds
        }
    
    def price_asian_option(
        self,
        S0: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = 'call',
        average_type: str = 'arithmetic',  # 'arithmetic' or 'geometric'
        n_paths: int = 100000,
        n_steps: int = 252,
        **model_params
    ) -> Dict[str, float]:
        """Price Asian option using Monte Carlo."""
        
        config = MCConfig(
            model=MonteCarloModel.GBM,
            n_paths=n_paths,
            n_steps=n_steps,
            time_horizon=T,
            params={
                'S0': S0,
                'mu': r,
                'sigma': sigma,
                **model_params
            }
        )
        
        result = self.run(config)
        
        if average_type == 'arithmetic':
            averages = np.mean(result.paths[:, 1:], axis=1)
        else:
            # Geometric average
            averages = np.exp(np.mean(np.log(result.paths[:, 1:]), axis=1))
        
        if option_type.lower() == 'call':
            payoffs = np.maximum(averages - K, 0)
        else:
            payoffs = np.maximum(K - averages, 0)
        
        price = np.exp(-r * T) * np.mean(payoffs)
        stderr = np.exp(-r * T) * np.std(payoffs) / np.sqrt(n_paths)
        
        return {
            'price': float(price),
            'std_error': float(stderr),
            'ci_lower': float(price - 1.96 * stderr),
            'ci_upper': float(price + 1.96 * stderr),
            'runtime': result.runtime_seconds
        }
    
    def price_barrier_option(
        self,
        S0: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        barrier: float,
        barrier_type: str = 'up-and-out',  # 'up-and-out', 'down-and-out', 'up-and-in', 'down-and-in'
        option_type: str = 'call',
        n_paths: int = 100000,
        n_steps: int = 252,
        **model_params
    ) -> Dict[str, float]:
        """Price barrier option using Monte Carlo."""
        
        config = MCConfig(
            model=MonteCarloModel.GBM,
            n_paths=n_paths,
            n_steps=n_steps,
            time_horizon=T,
            params={
                'S0': S0,
                'mu': r,
                'sigma': sigma,
                **model_params
            }
        )
        
        result = self.run(config)
        paths = result.paths
        final_spots = paths[:, -1]
        
        # Check barrier conditions
        if 'up' in barrier_type:
            barrier_hit = np.any(paths >= barrier, axis=1)
        else:
            barrier_hit = np.any(paths <= barrier, axis=1)
        
        if 'out' in barrier_type:
            active = ~barrier_hit
        else:  # 'in'
            active = barrier_hit
        
        if option_type.lower() == 'call':
            payoffs = np.maximum(final_spots - K, 0)
        else:
            payoffs = np.maximum(K - final_spots, 0)
        
        payoffs = payoffs * active
        
        price = np.exp(-r * T) * np.mean(payoffs)
        stderr = np.exp(-r * T) * np.std(payoffs) / np.sqrt(n_paths)
        
        return {
            'price': float(price),
            'std_error': float(stderr),
            'ci_lower': float(price - 1.96 * stderr),
            'ci_upper': float(price + 1.96 * stderr),
            'runtime': result.runtime_seconds
        }
    
    def price_american_option(
        self,
        S0: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = 'put',
        n_paths: int = 50000,
        n_steps: int = 252,
        regression_degree: int = 3
    ) -> Dict[str, float]:
        """Price American option using Longstaff-Schwartz LSM."""
        
        config = MCConfig(
            model=MonteCarloModel.GBM,
            n_paths=n_paths,
            n_steps=n_steps,
            time_horizon=T,
            params={'S0': S0, 'mu': r, 'sigma': sigma}
        )
        
        result = self.run(config)
        paths = result.paths
        dt = T / n_steps
        df = np.exp(-r * dt)
        
        # Cash flows at maturity
        if option_type.lower() == 'put':
            cashflows = np.maximum(K - paths[:, -1], 0)
        else:
            cashflows = np.maximum(paths[:, -1] - K, 0)
        
        # Backward induction
        for t in range(n_steps - 1, 0, -1):
            current_spots = paths[:, t]
            continuation_mask = (
                (option_type.lower() == 'put' and current_spots < K) or
                (option_type.lower() == 'call' and current_spots > K)
            )
            
            if np.any(continuation_mask):
                # Regression
                X = current_spots[continuation_mask]
                Y = cashflows[continuation_mask] * df
                
                # Polynomial regression
                coeffs = np.polyfit(X, Y, regression_degree)
                continuation_value = np.polyval(coeffs, X)
                
                # Exercise value
                if option_type.lower() == 'put':
                    exercise_value = np.maximum(K - X, 0)
                else:
                    exercise_value = np.maximum(X - K, 0)
                
                # Optimal exercise
                exercise = exercise_value > continuation_value
                
                exercise_indices = np.where(continuation_mask)[0][exercise]
                cashflows[exercise_indices] = exercise_value[exercise]
                cashflows[exercise_indices] = np.exp(-r * (T - t * dt)) * cashflows[exercise_indices]
        
        # Discount to present
        price = np.mean(cashflows) * np.exp(-r * dt)
        stderr = np.std(cashflows) * np.exp(-r * dt) / np.sqrt(n_paths)
        
        return {
            'price': float(price),
            'std_error': float(stderr),
            'ci_lower': float(price - 1.96 * stderr),
            'ci_upper': float(price + 1.96 * stderr),
            'runtime': result.runtime_seconds
        }


# ============================================================
# Factory
# ============================================================

def create_monte_carlo_engine(dist_engine: DistributionEngine = None) -> MonteCarloEngine:
    """Create Monte Carlo engine instance."""
    return MonteCarloEngine(dist_engine)


# ============================================================
# Variance Reduction Techniques
# ============================================================

class VarianceReduction:
    """Variance reduction techniques for Monte Carlo."""
    
    @staticmethod
    def antithetic_variates(Z: np.ndarray) -> np.ndarray:
        """Apply antithetic variates."""
        return np.vstack([Z, -Z])
    
    @staticmethod
    def control_variate(
        payoffs: np.ndarray,
        control_payoffs: np.ndarray,
        control_mean: float,
        beta: float = None
    ) -> np.ndarray:
        """Apply control variate method."""
        if beta is None:
            # Optimal beta
            cov = np.cov(payoffs, control_payoffs)[0, 1]
            var_control = np.var(control_payoffs)
            beta = cov / var_control if var_control > 0 else 0
        
        adjusted = payoffs - beta * (control_payoffs - control_mean)
        return adjusted
    
    @staticmethod
    def importance_sampling(
        target_density: Callable,
        proposal_density: Callable,
        proposal_sampler: Callable,
        n_samples: int,
        function: Callable
    ) -> Tuple[float, float]:
        """Importance sampling estimator."""
        samples = proposal_sampler(n_samples)
        weights = target_density(samples) / proposal_density(samples)
        weighted_values = function(samples) * weights
        
        estimate = np.mean(weighted_values)
        stderr = np.std(weighted_values) / np.sqrt(n_samples)
        
        return estimate, stderr
    
    @staticmethod
    def stratified_sampling(
        strata_bounds: List[Tuple[float, float]],
        n_per_stratum: int,
        sampler: Callable,
        function: Callable
    ) -> Tuple[float, float]:
        """Stratified sampling."""
        n_strata = len(strata_bounds)
        total_n = n_strata * n_per_stratum
        
        estimates = []
        for low, high in strata_bounds:
            stratum_samples = sampler(n_per_stratum, low, high)
            stratum_values = function(stratum_samples)
            estimates.append(np.mean(stratum_values))
        
        # Weighted average
        weights = [(high - low) for low, high in strata_bounds]
        weights = np.array(weights) / sum(weights)
        
        estimate = np.sum(weights * np.array(estimates))
        # Variance estimation would need more work
        stderr = np.std(estimates) / np.sqrt(n_strata)
        
        return estimate, stderr