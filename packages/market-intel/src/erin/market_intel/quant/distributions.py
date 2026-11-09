"""Distribution Engine - Statistical distributions for quantitative finance."""

import numpy as np
import scipy.stats as stats
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from erin.market_intel.domain.interfaces import CurrencyCode


class DistributionType(str, Enum):
    NORMAL = "NORMAL"
    LOG_NORMAL = "LOG_NORMAL"
    STUDENT_T = "STUDENT_T"
    SKEWED_T = "SKEWED_T"
    GENERALIZED_HYPERBOLIC = "GENERALIZED_HYPERBOLIC"
    NIG = "NIG"  # Normal Inverse Gaussian
    VG = "VG"    # Variance Gamma
    CGMY = "CGMY"
    GARCH = "GARCH"


@dataclass
class DistributionParams:
    """Parameters for a statistical distribution."""
    dist_type: DistributionType
    params: Dict[str, float]  # Distribution-specific parameters
    
    def get_param(self, name: str, default: float = 0.0) -> float:
        return self.params.get(name, default)


@dataclass
class DistributionFit:
    """Result of distribution fitting."""
    dist_type: DistributionType
    params: Dict[str, float]
    log_likelihood: float
    aic: float
    bic: float
    ks_statistic: float
    ks_p_value: float
    converged: bool


class DistributionEngine:
    """Statistical distribution engine for financial modeling."""
    
    def __init__(self):
        self._distributions = {
            DistributionType.NORMAL: self._normal_dist,
            DistributionType.LOG_NORMAL: self._log_normal_dist,
            DistributionType.STUDENT_T: self._student_t_dist,
            DistributionType.SKEWED_T: self._skewed_t_dist,
            DistributionType.NIG: self._nig_dist,
            DistributionType.VG: self._vg_dist,
            DistributionType.CGMY: self._cgmy_dist,
        }
    
    # ============================================================
    # Distribution Functions (PDF, CDF, PPF, RVS)
    # ============================================================
    
    def _normal_dist(self, params: Dict[str, float]):
        """Normal distribution."""
        loc = params.get('loc', 0.0)
        scale = params.get('scale', 1.0)
        return stats.norm(loc=loc, scale=scale)
    
    def _log_normal_dist(self, params: Dict[str, float]):
        """Log-normal distribution."""
        s = params.get('s', 1.0)  # shape parameter (sigma)
        scale = params.get('scale', 1.0)  # exp(mu)
        return stats.lognorm(s=s, scale=scale)
    
    def _student_t_dist(self, params: Dict[str, float]):
        """Student's t-distribution."""
        df = params.get('df', 5.0)
        loc = params.get('loc', 0.0)
        scale = params.get('scale', 1.0)
        return stats.t(df=df, loc=loc, scale=scale)
    
    def _skewed_t_dist(self, params: Dict[str, float]):
        """Skewed t-distribution (Fernandez & Steel)."""
        df = params.get('df', 5.0)
        loc = params.get('loc', 0.0)
        scale = params.get('scale', 1.0)
        skew = params.get('skew', 0.0)  # skewness parameter
        
        # Use scipy's skewed t if available, otherwise approximate
        try:
            from scipy.stats import skewt
            return skewt(df=df, loc=loc, scale=scale, a=skew)
        except ImportError:
            # Fallback to regular t
            return stats.t(df=df, loc=loc, scale=scale)
    
    def _nig_dist(self, params: Dict[str, float]):
        """Normal Inverse Gaussian distribution."""
        # NIG parameters: alpha, beta, delta, mu
        # scipy doesn't have NIG directly, use approximation
        alpha = params.get('alpha', 1.0)
        beta = params.get('beta', 0.0)
        delta = params.get('delta', 1.0)
        mu = params.get('mu', 0.0)
        
        # Use t-distribution as approximation
        df = 2 * alpha * delta
        return stats.t(df=max(df, 2.1), loc=mu, scale=scale)
    
    def _vg_dist(self, params: Dict[str, float]):
        """Variance Gamma distribution."""
        # VG parameters: theta, sigma, nu, mu
        theta = params.get('theta', 0.0)
        sigma = params.get('sigma', 1.0)
        nu = params.get('nu', 1.0)
        mu = params.get('mu', 0.0)
        
        # Approximate with t-distribution
        return stats.t(df=max(2.1, 2/nu), loc=mu, scale=sigma)
    
    def _cgmy_dist(self, params: Dict[str, float]):
        """CGMY (Carr-Geman-Madan-Yor) distribution."""
        # CGMY parameters: C, G, M, Y
        C = params.get('C', 1.0)
        G = params.get('G', 5.0)
        M = params.get('M', 5.0)
        Y = params.get('Y', 0.5)
        
        # Approximate with t-distribution
        return stats.t(df=max(2.1, 2/Y), loc=0, scale=1)
    
    def get_distribution(self, dist_type: DistributionType, params: Dict[str, float]):
        """Get scipy distribution object."""
        if dist_type not in self._distributions:
            raise ValueError(f"Unsupported distribution: {dist_type}")
        return self._distributions[dist_type](params)
    
    def pdf(self, x: float, dist_type: DistributionType, params: Dict[str, float]) -> float:
        """Probability density function."""
        dist = self.get_distribution(dist_type, params)
        return dist.pdf(x)
    
    def cdf(self, x: float, dist_type: DistributionType, params: Dict[str, float]) -> float:
        """Cumulative distribution function."""
        dist = self.get_distribution(dist_type, params)
        return dist.cdf(x)
    
    def ppf(self, q: float, dist_type: DistributionType, params: Dict[str, float]) -> float:
        """Percent point function (inverse CDF)."""
        dist = self.get_distribution(dist_type, params)
        return dist.ppf(q)
    
    def rvs(self, size: int, dist_type: DistributionType, params: Dict[str, float]) -> np.ndarray:
        """Random variates."""
        dist = self.get_distribution(dist_type, params)
        return dist.rvs(size=size)
    
    # ============================================================
    # Moment Calculations
    # ============================================================
    
    def moments(self, dist_type: DistributionType, params: Dict[str, float]) -> Dict[str, float]:
        """Calculate theoretical moments."""
        dist = self.get_distribution(dist_type, params)
        
        return {
            'mean': float(dist.mean()),
            'variance': float(dist.var()),
            'skewness': float(dist.stats(moments='s')),
            'kurtosis': float(dist.stats(moments='k')),
        }
    
    def moment(self, order: int, dist_type: DistributionType, params: Dict[str, float]) -> float:
        """Calculate raw moment of given order."""
        dist = self.get_distribution(dist_type, params)
        return float(dist.moment(order))
    
    # ============================================================
    # Distribution Fitting (MLE)
    # ============================================================
    
    def fit(
        self,
        data: np.ndarray,
        dist_type: DistributionType,
        initial_params: Dict[str, float] = None
    ) -> DistributionFit:
        """Fit distribution to data using MLE."""
        if dist_type not in self._distributions:
            raise ValueError(f"Unsupported distribution for fitting: {dist_type}")
        
        dist_class = self._get_scipy_class(dist_type)
        if dist_class is None:
            raise ValueError(f"Cannot fit {dist_type} - no scipy class available")
        
        # Fit using scipy
        try:
            if initial_params:
                fitted_params = dist_class.fit(data, **initial_params)
            else:
                fitted_params = dist_class.fit(data)
            
            # Build param dict
            param_names = dist_class._argnames if hasattr(dist_class, '_argnames') else []
            param_dict = dict(zip(param_names, fitted_params))
            
            # Calculate log-likelihood
            log_likelihood = np.sum(dist_class.logpdf(data, *fitted_params))
            
            # AIC/BIC
            n_params = len(fitted_params)
            n_obs = len(data)
            aic = 2 * n_params - 2 * log_likelihood
            bic = n_params * np.log(n_obs) - 2 * log_likelihood
            
            # KS test
            fitted_dist = dist_class(*fitted_params)
            ks_stat, ks_p = stats.kstest(data, fitted_dist.cdf)
            
            return DistributionFit(
                dist_type=dist_type,
                params=param_dict,
                log_likelihood=float(log_likelihood),
                aic=float(aic),
                bic=float(bic),
                ks_statistic=float(ks_stat),
                ks_p_value=float(ks_p),
                converged=True
            )
        except Exception as e:
            raise ValueError(f"Fitting failed: {e}")
    
    def fit_multiple(
        self,
        data: np.ndarray,
        dist_types: List[DistributionType] = None
    ) -> List[DistributionFit]:
        """Fit multiple distributions and return sorted by AIC."""
        dist_types = dist_types or [
            DistributionType.NORMAL,
            DistributionType.STUDENT_T,
            DistributionType.SKEWED_T,
            DistributionType.LOG_NORMAL,
        ]
        
        results = []
        for dist_type in dist_types:
            try:
                fit_result = self.fit(data, dist_type)
                results.append(fit_result)
            except Exception as e:
                pass  # Skip failed fits
        
        # Sort by AIC (lower is better)
        results.sort(key=lambda x: x.aic)
        return results
    
    def _get_scipy_class(self, dist_type: DistributionType):
        """Get scipy distribution class for fitting."""
        mapping = {
            DistributionType.NORMAL: stats.norm,
            DistributionType.LOG_NORMAL: stats.lognorm,
            DistributionType.STUDENT_T: stats.t,
        }
        
        # Skewed t not directly available in scipy
        if dist_type == DistributionType.SKEWED_T:
            return stats.t  # Use regular t as fallback
        
        return mapping.get(dist_type)
    
    # ============================================================
    # VaR/ES Calculations
    # ============================================================
    
    def var(
        self,
        confidence: float,
        dist_type: DistributionType,
        params: Dict[str, float]
    ) -> float:
        """Value at Risk (negative quantile)."""
        return -self.ppf(1 - confidence, dist_type, params)
    
    def es(
        self,
        confidence: float,
        dist_type: DistributionType,
        params: Dict[str, float],
        n_samples: int = 100000
    ) -> float:
        """Expected Shortfall (Conditional VaR)."""
        # Monte Carlo estimation
        samples = self.rvs(n_samples, dist_type, params)
        var_threshold = -self.var(confidence, dist_type, params)
        tail_losses = samples[samples <= var_threshold]
        
        if len(tail_losses) > 0:
            return -float(np.mean(tail_losses))
        return -self.ppf(1 - confidence, dist_type, params)
    
    def cornish_fisher_var(
        self,
        confidence: float,
        mean: float,
        std: float,
        skew: float,
        kurt: float
    ) -> float:
        """Cornish-Fisher VaR accounting for skewness and kurtosis."""
        from scipy.stats import norm
        
        z = norm.ppf(1 - confidence)
        
        # Cornish-Fisher expansion
        z_cf = (z + 
                (z**2 - 1) * skew / 6 +
                (z**3 - 3*z) * kurt / 24 -
                (2*z**3 - 5*z) * skew**2 / 36)
        
        return -(mean + z_cf * std)
    
    # ============================================================
    # Risk-Neutral Measure Transformation
    # ============================================================
    
    def esscher_transform(
        self,
        dist_type: DistributionType,
        params: Dict[str, float],
        theta: float
    ) -> Dict[str, float]:
        """Esscher transform for risk-neutral measure."""
        # For normal: shift mean by theta * variance
        if dist_type == DistributionType.NORMAL:
            new_params = params.copy()
            new_params['loc'] = params.get('loc', 0) + theta * params.get('scale', 1)**2
            return new_params
        
        # For Student's t: approximate
        return params
    
    def risk_neutral_params(
        self,
        dist_type: DistributionType,
        physical_params: Dict[str, float],
        risk_free_rate: float,
        dividend_yield: float = 0.0
    ) -> Dict[str, float]:
        """Convert physical to risk-neutral parameters."""
        if dist_type == DistributionType.NORMAL:
            rn_params = physical_params.copy()
            rn_params['loc'] = (risk_free_rate - dividend_yield - 0.5 * physical_params.get('scale', 0)**2)
            return rn_params
        
        return physical_params


# ============================================================
# GARCH Model
# ============================================================

class GARCHModel:
    """GARCH(1,1) volatility model."""
    
    def __init__(self):
        self.omega = 0.0
        self.alpha = 0.0
        self.beta = 0.0
        self.fitted = False
    
    def fit(self, returns: np.ndarray) -> Dict[str, float]:
        """Fit GARCH(1,1) using MLE."""
        from scipy.optimize import minimize
        
        def neg_log_likelihood(params):
            omega, alpha, beta = params
            if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
                return 1e10
            
            n = len(returns)
            sigma2 = np.zeros(n)
            sigma2[0] = np.var(returns)
            
            log_lik = 0
            for t in range(1, n):
                sigma2[t] = omega + alpha * returns[t-1]**2 + beta * sigma2[t-1]
                if sigma2[t] <= 0:
                    return 1e10
                log_lik += -0.5 * (np.log(2*np.pi) + np.log(sigma2[t]) + returns[t]**2 / sigma2[t])
            
            return -log_lik
        
        # Initial guess
        init = [0.1 * np.var(returns), 0.1, 0.85]
        bounds = [(1e-6, None), (1e-6, 1), (1e-6, 1)]
        constraints = {'type': 'ineq', 'fun': lambda x: 1 - x[1] - x[2]}
        
        result = minimize(neg_log_likelihood, init, bounds=bounds, constraints=constraints)
        
        if result.success:
            self.omega, self.alpha, self.beta = result.x
            self.fitted = True
            return {
                'omega': float(self.omega),
                'alpha': float(self.alpha),
                'beta': float(self.beta),
                'log_likelihood': -float(result.fun),
                'persistence': float(self.alpha + self.beta),
                'half_life': float(np.log(0.5) / np.log(self.alpha + self.beta)) if self.alpha + self.beta < 1 else float('inf')
            }
        else:
            raise ValueError("GARCH fitting failed")
    
    def forecast(self, returns: np.ndarray, horizon: int = 1) -> np.ndarray:
        """Forecast conditional variance."""
        if not self.fitted:
            raise ValueError("Model not fitted")
        
        n = len(returns)
        sigma2 = np.zeros(n)
        sigma2[0] = np.var(returns)
        
        # Calculate in-sample variances
        for t in range(1, n):
            sigma2[t] = self.omega + self.alpha * returns[t-1]**2 + self.beta * sigma2[t-1]
        
        # Forecast
        forecasts = np.zeros(horizon)
        last_return = returns[-1]
        last_var = sigma2[-1]
        
        for h in range(horizon):
            if h == 0:
                forecasts[h] = self.omega + self.alpha * last_return**2 + self.beta * last_var
            else:
                forecasts[h] = self.omega + (self.alpha + self.beta) * forecasts[h-1]
            
            # Long-run variance
            if h > 0:
                forecasts[h] = self.omega / (1 - self.alpha - self.beta) + \
                              (forecasts[h] - self.omega / (1 - self.alpha - self.beta)) * \
                              (self.alpha + self.beta)**h
        
        return forecasts
    
    def simulate(self, n_steps: int, n_paths: int = 1) -> np.ndarray:
        """Simulate returns paths."""
        if not self.fitted:
            raise ValueError("Model not fitted")
        
        paths = np.zeros((n_paths, n_steps))
        
        for p in range(n_paths):
            sigma2 = np.var(np.random.randn(100))  # Initial variance
            for t in range(n_steps):
                # Generate return
                z = np.random.randn()
                r = np.sqrt(sigma2) * z
                paths[p, t] = r
                
                # Update variance
                sigma2 = self.omega + self.alpha * r**2 + self.beta * sigma2
        
        return paths


# ============================================================
# Factory
# ============================================================

def create_distribution_engine() -> DistributionEngine:
    """Create distribution engine instance."""
    return DistributionEngine()

def create_garch_model() -> GARCHModel:
    """Create GARCH model instance."""
    return GARCHModel()