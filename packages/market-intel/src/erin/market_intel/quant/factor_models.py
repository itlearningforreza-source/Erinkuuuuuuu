"""Factor Models - Fama-French, Carhart, Barra-style, and custom factor models."""

import numpy as np
import scipy.stats as stats
import scipy.optimize as optimize
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    import pandas as pd


class FactorModelType(str, Enum):
    CAPM = "CAPM"
    FAMA_FRENCH_3 = "FAMA_FRENCH_3"
    FAMA_FRENCH_5 = "FAMA_FRENCH_5"
    CARHART_4 = "CARHART_4"
    BARRA = "BARRA"
    PCA = "PCA"
    CUSTOM = "CUSTOM"


class RegressionMethod(str, Enum):
    OLS = "OLS"
    WLS = "WLS"          # Weighted Least Squares
    GLS = "GLS"          # Generalized Least Squares
    ROBUST = "ROBUST"    # Huber/Huber-White


@dataclass
class FactorModelConfig:
    """Configuration for factor model."""
    model_type: FactorModelType
    factors: List[str] = field(default_factory=list)
    regression_method: RegressionMethod = RegressionMethod.OLS
    weight_column: Optional[str] = None
    robust_method: str = "huber"  # 'huber', 'tukey', 'hampel'
    include_intercept: bool = True
    standardize: bool = False


@dataclass
class FactorRegressionResult:
    """Result of factor regression."""
    model_type: FactorModelType
    alpha: float
    alpha_t_stat: float
    alpha_p_value: float
    betas: Dict[str, float]
    beta_t_stats: Dict[str, float]
    beta_p_values: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_p_value: float
    residuals: np.ndarray
    fitted_values: np.ndarray
    covariance_matrix: np.ndarray
    n_observations: int
    n_factors: int


@dataclass
class FactorExposure:
    """Factor exposure for a single asset."""
    date: str
    asset_id: str
    exposures: Dict[str, float]
    r_squared: float


class FactorModelEngine:
    """Factor model estimation and risk decomposition engine."""
    
    def __init__(self):
        self._factor_data = {}
        self._models = {}
    
    def set_factor_data(self, factor_data: Dict[str, np.ndarray], dates: np.ndarray = None):
        """Set factor return data."""
        self._factor_data = factor_data
        self._factor_dates = dates
    
    def load_fama_french_factors(
        self,
        factor_returns: Dict[str, np.ndarray],
        dates: np.ndarray = None
    ):
        """Load Fama-French factor returns."""
        required = ['MKT-RF', 'SMB', 'HML']
        for f in required:
            if f not in factor_returns:
                raise ValueError(f"Missing required factor: {f}")
        
        self._factor_data.update(factor_returns)
        self._factor_dates = dates
    
    def load_fama_french_5_factors(
        self,
        factor_returns: Dict[str, np.ndarray],
        dates: np.ndarray = None
    ):
        """Load Fama-French 5-factor data."""
        required = ['MKT-RF', 'SMB', 'HML', 'RMW', 'CMA']
        for f in required:
            if f not in factor_returns:
                raise ValueError(f"Missing required factor: {f}")
        
        self._factor_data.update(factor_returns)
        self._factor_dates = dates
    
    def load_carhart_4_factors(
        self,
        factor_returns: Dict[str, np.ndarray],
        dates: np.ndarray = None
    ):
        """Load Carhart 4-factor data."""
        required = ['MKT-RF', 'SMB', 'HML', 'MOM']
        for f in required:
            if f not in factor_returns:
                raise ValueError(f"Missing required factor: {f}")
        
        self._factor_data.update(factor_returns)
        self._factor_dates = dates
    
    def run_regression(
        self,
        asset_returns: np.ndarray,
        factor_names: List[str] = None,
        config: FactorModelConfig = None
    ) -> FactorRegressionResult:
        """Run factor regression for a single asset."""
        
        if config is None:
            config = FactorModelConfig(model_type=FactorModelType.CUSTOM)
        
        if factor_names is None:
            factor_names = list(self._factor_data.keys())
        
        # Prepare factor matrix
        X = np.column_stack([self._factor_data[f] for f in factor_names])
        y = asset_returns
        
        # Align lengths
        min_len = min(len(y), len(X))
        y = y[:min_len]
        X = X[:min_len]
        
        # Add intercept
        if config.include_intercept:
            X = np.column_stack([np.ones(min_len), X])
            param_names = ['alpha'] + factor_names
        else:
            param_names = factor_names
        
        # Standardize if requested
        if config.standardize:
            X_mean = X.mean(axis=0)
            X_std = X.std(axis=0)
            X_std[X_std == 0] = 1
            X = (X - X_mean) / X_std
            y_mean = y.mean()
            y_std = y.std()
            y = (y - y_mean) / y_std
        
        # Run regression
        if config.regression_method == RegressionMethod.OLS:
            result = self._ols_regression(y, X, param_names)
        elif config.regression_method == RegressionMethod.WLS:
            result = self._wls_regression(y, X, param_names, config.weight_column)
        elif config.regression_method == RegressionMethod.ROBUST:
            result = self._robust_regression(y, X, param_names, config.robust_method)
        else:
            result = self._ols_regression(y, X, param_names)
        
        return result
    
    def _ols_regression(
        self,
        y: np.ndarray,
        X: np.ndarray,
        param_names: List[str]
    ) -> FactorRegressionResult:
        """Ordinary Least Squares regression."""
        
        # OLS: beta = (X'X)^(-1) X'y
        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            # Use pseudo-inverse
            beta = np.linalg.pinv(X) @ y
        
        n_obs, n_params = X.shape
        fitted = X @ beta
        residuals = y - fitted
        
        # R-squared
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - y.mean())**2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        adj_r_squared = 1 - (1 - r_squared) * (n_obs - 1) / (n_obs - n_params)
        
        # Covariance matrix
        sigma2 = ss_res / (n_obs - n_params)
        cov_matrix = sigma2 * np.linalg.pinv(X.T @ X)
        
        # Standard errors
        se = np.sqrt(np.diag(cov_matrix))
        
        # t-stats and p-values
        t_stats = beta / se
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n_obs - n_params))
        
        # F-statistic
        if n_params > 1:
            ss_reg = np.sum((fitted - y.mean())**2)
            f_stat = (ss_reg / (n_params - 1)) / (ss_res / (n_obs - n_params))
            f_p = 1 - stats.f.cdf(f_stat, n_params - 1, n_obs - n_params)
        else:
            f_stat = t_stats[0]**2
            f_p = p_values[0]
        
        # Extract alpha and betas
        alpha_idx = 0 if param_names[0] == 'alpha' else None
        alpha = beta[alpha_idx] if alpha_idx is not None else 0.0
        alpha_t = t_stats[alpha_idx] if alpha_idx is not None else 0.0
        alpha_p = p_values[alpha_idx] if alpha_idx is not None else 1.0
        
        betas = {}
        beta_t = {}
        beta_p = {}
        
        start = 1 if alpha_idx is not None else 0
        for i, name in enumerate(param_names[start:], start=start):
            betas[name] = beta[i]
            beta_t[name] = t_stats[i]
            beta_p[name] = p_values[i]
        
        return FactorRegressionResult(
            model_type=FactorModelType.CUSTOM,
            alpha=float(alpha),
            alpha_t_stat=float(alpha_t),
            alpha_p_value=float(alpha_p),
            betas={k: float(v) for k, v in betas.items()},
            beta_t_stats={k: float(v) for k, v in beta_t.items()},
            beta_p_values={k: float(v) for k, v in beta_p.items()},
            r_squared=float(r_squared),
            adj_r_squared=float(adj_r_squared),
            f_statistic=float(f_stat),
            f_p_value=float(f_p),
            residuals=residuals,
            fitted_values=fitted,
            covariance_matrix=cov_matrix,
            n_observations=n_obs,
            n_factors=len(betas)
        )
    
    def _wls_regression(
        self,
        y: np.ndarray,
        X: np.ndarray,
        param_names: List[str],
        weights: np.ndarray = None
    ) -> FactorRegressionResult:
        """Weighted Least Squares regression."""
        
        if weights is None:
            weights = np.ones(len(y))
        
        W = np.diag(weights)
        XTWX = X.T @ W @ X
        XTWy = X.T @ W @ y
        
        try:
            beta = np.linalg.solve(XTWX, XTWy)
        except np.linalg.LinAlgError:
            beta = np.linalg.pinv(XTWX) @ XTWy
        
        # Similar to OLS but with weighted calculations
        fitted = X @ beta
        residuals = y - fitted
        
        # Weighted R-squared
        ss_res_w = np.sum(weights * residuals**2)
        ss_tot_w = np.sum(weights * (y - np.average(y, weights=weights))**2)
        r_squared = 1 - ss_res_w / ss_tot_w if ss_tot_w > 0 else 0
        
        # Covariance matrix
        n_obs, n_params = X.shape
        sigma2 = ss_res_w / (n_obs - n_params)
        cov_matrix = sigma2 * np.linalg.pinv(XTWX)
        
        se = np.sqrt(np.diag(cov_matrix))
        t_stats = beta / se
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n_obs - n_params))
        
        # Alpha and betas
        alpha_idx = 0 if param_names[0] == 'alpha' else None
        alpha = beta[alpha_idx] if alpha_idx is not None else 0.0
        alpha_t = t_stats[alpha_idx] if alpha_idx is not None else 0.0
        alpha_p = p_values[alpha_idx] if alpha_idx is not None else 1.0
        
        betas = {}
        beta_t = {}
        beta_p = {}
        start = 1 if alpha_idx is not None else 0
        for i, name in enumerate(param_names[start:], start=start):
            betas[name] = beta[i]
            beta_t[name] = t_stats[i]
            beta_p[name] = p_values[i]
        
        return FactorRegressionResult(
            model_type=FactorModelType.CUSTOM,
            alpha=float(alpha),
            alpha_t_stat=float(alpha_t),
            alpha_p_value=float(alpha_p),
            betas={k: float(v) for k, v in betas.items()},
            beta_t_stats={k: float(v) for k, v in beta_t.items()},
            beta_p_values={k: float(v) for k, v in beta_p.items()},
            r_squared=float(r_squared),
            adj_r_squared=float(r_squared),  # Approximate
            f_statistic=0.0,
            f_p_value=1.0,
            residuals=residuals,
            fitted_values=fitted,
            covariance_matrix=cov_matrix,
            n_observations=len(y),
            n_factors=len(betas)
        )
    
    def _robust_regression(
        self,
        y: np.ndarray,
        X: np.ndarray,
        param_names: List[str],
        method: str = "huber"
    ) -> FactorRegressionResult:
        """Robust regression using Huber or other loss functions."""
        
        from scipy.optimize import minimize
        
        n_obs, n_params = X.shape
        
        def huber_loss(residuals, delta=1.345):
            abs_res = np.abs(residuals)
            return np.where(abs_res <= delta,
                           0.5 * residuals**2,
                           delta * (abs_res - 0.5 * delta))
        
        def objective(beta):
            residuals = y - X @ beta
            return np.sum(huber_loss(residuals))
        
        # Initial guess from OLS
        beta_init = np.linalg.lstsq(X, y, rcond=None)[0]
        
        result = minimize(objective, beta_init, method='BFGS')
        
        if not result.success:
            warnings.warn("Robust regression did not converge, falling back to OLS")
            return self._ols_regression(y, X, param_names)
        
        beta = result.x
        fitted = X @ beta
        residuals = y - fitted
        
        # Calculate statistics using robust covariance
        # Huber-White sandwich estimator
        residuals_sq = residuals**2
        # Weight by Huber psi function
        delta = 1.345
        psi = np.where(np.abs(residuals) <= delta,
                      residuals,
                      delta * np.sign(residuals))
        
        # Sandwich covariance
        meat = X.T @ np.diag(psi**2) @ X
        bread = np.linalg.pinv(X.T @ X)
        cov_matrix = bread @ meat @ bread
        
        se = np.sqrt(np.diag(cov_matrix))
        t_stats = beta / se
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n_obs - n_params))
        
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - y.mean())**2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        
        alpha_idx = 0 if param_names[0] == 'alpha' else None
        alpha = beta[alpha_idx] if alpha_idx is not None else 0.0
        alpha_t = t_stats[alpha_idx] if alpha_idx is not None else 0.0
        alpha_p = p_values[alpha_idx] if alpha_idx is not None else 1.0
        
        betas = {}
        beta_t = {}
        beta_p = {}
        start = 1 if alpha_idx is not None else 0
        for i, name in enumerate(param_names[start:], start=start):
            betas[name] = beta[i]
            beta_t[name] = t_stats[i]
            beta_p[name] = p_values[i]
        
        return FactorRegressionResult(
            model_type=FactorModelType.CUSTOM,
            alpha=float(alpha),
            alpha_t_stat=float(alpha_t),
            alpha_p_value=float(alpha_p),
            betas={k: float(v) for k, v in betas.items()},
            beta_t_stats={k: float(v) for k, v in beta_t.items()},
            beta_p_values={k: float(v) for k, v in beta_p.items()},
            r_squared=float(r_squared),
            adj_r_squared=float(r_squared),
            f_statistic=0.0,
            f_p_value=1.0,
            residuals=residuals,
            fitted_values=fitted,
            covariance_matrix=cov_matrix,
            n_observations=n_obs,
            n_factors=len(betas)
        )
    
    def run_rolling_regression(
        self,
        asset_returns: np.ndarray,
        window: int = 60,
        factor_names: List[str] = None,
        config: FactorModelConfig = None,
        min_periods: int = 30
    ) -> List[Dict]:
        """Run rolling window factor regression."""
        
        results = []
        n = len(asset_returns)
        
        for i in range(window, n):
            window_returns = asset_returns[i-window:i]
            
            if len(window_returns) < min_periods:
                continue
            
            try:
                result = self.run_regression(window_returns, factor_names, config)
                results.append({
                    'window_end': i,
                    'alpha': result.alpha,
                    'alpha_t': result.alpha_t_stat,
                    'alpha_p': result.alpha_p_value,
                    'betas': result.betas,
                    'beta_t_stats': result.beta_t_stats,
                    'r_squared': result.r_squared,
                    'n_obs': result.n_observations
                })
            except Exception as e:
                pass
        
        return results
    
    def run_panel_regression(
        self,
        asset_returns: Dict[str, np.ndarray],  # asset_id -> returns
        factor_names: List[str] = None,
        config: FactorModelConfig = None
    ) -> Dict[str, FactorRegressionResult]:
        """Run factor regression for multiple assets."""
        
        results = {}
        for asset_id, returns in asset_returns.items():
            try:
                result = self.run_regression(returns, factor_names, config)
                results[asset_id] = result
            except Exception as e:
                pass
        return results
    
    def get_factor_covariance(self, factor_names: List[str] = None) -> np.ndarray:
        """Get factor covariance matrix."""
        if factor_names is None:
            factor_names = list(self._factor_data.keys())
        
        X = np.column_stack([self._factor_data[f] for f in factor_names])
        return np.cov(X, rowvar=False)
    
    def get_factor_correlation(self, factor_names: List[str] = None) -> np.ndarray:
        """Get factor correlation matrix."""
        cov = self.get_factor_covariance(factor_names)
        std = np.sqrt(np.diag(cov))
        corr = cov / np.outer(std, std)
        return corr


class RiskDecomposition:
    """Risk decomposition using factor models."""
    
    def __init__(self, factor_engine: FactorModelEngine):
        self.factor_engine = factor_engine
    
    def decompose_portfolio_risk(
        self,
        portfolio_weights: Dict[str, float],
        asset_returns: Dict[str, np.ndarray],
        factor_names: List[str] = None,
        config: FactorModelConfig = None
    ) -> Dict[str, Any]:
        """Decompose portfolio risk into factor and idiosyncratic components."""
        
        # Run factor regressions for all assets
        regression_results = self.factor_engine.run_panel_regression(
            asset_returns, factor_names, config
        )
        
        # Portfolio weights vector
        assets = list(portfolio_weights.keys())
        w = np.array([portfolio_weights[a] for a in assets])
        
        # Factor exposures matrix (n_assets x n_factors)
        if factor_names is None:
            factor_names = list(self.factor_engine._factor_data.keys())
        n_factors = len(factor_names)
        
        B = np.zeros((len(assets), n_factors))
        idio_vars = np.zeros(len(assets))
        
        for i, asset in enumerate(assets):
            if asset in regression_results:
                res = regression_results[asset]
                for j, fname in enumerate(factor_names):
                    B[i, j] = res.betas.get(fname, 0)
                idio_vars[i] = np.var(res.residuals)
        
        # Factor covariance matrix
        F = self.factor_engine.get_factor_covariance(factor_names)
        
        # Portfolio factor exposures
        portfolio_betas = w @ B  # (n_factors,)
        
        # Factor risk
        factor_risk = portfolio_betas @ F @ portfolio_betas
        
        # Idiosyncratic risk
        D = np.diag(idio_vars)
        idio_risk = w @ D @ w
        
        # Total risk
        total_risk = factor_risk + idio_risk
        
        # Risk contributions
        factor_contrib = B.T @ F @ portfolio_betas * w
        idio_contrib = idio_vars * w**2
        
        return {
            'total_variance': float(total_risk),
            'factor_variance': float(factor_risk),
            'idiosyncratic_variance': float(idio_risk),
            'factor_risk_pct': float(factor_risk / total_risk) if total_risk > 0 else 0,
            'idiosyncratic_risk_pct': float(idio_risk / total_risk) if total_risk > 0 else 0,
            'portfolio_betas': {f: float(b) for f, b in zip(factor_names, portfolio_betas)},
            'factor_contributions': {a: float(fc) for a, fc in zip(assets, factor_contrib)},
            'idiosyncratic_contributions': {a: float(ic) for a, ic in zip(assets, idio_contrib)},
            'tracking_error': float(np.sqrt(total_risk)),
        }
    
    def marginal_contribution_to_risk(
        self,
        portfolio_weights: Dict[str, float],
        asset_returns: Dict[str, np.ndarray],
        factor_names: List[str] = None
    ) -> Dict[str, float]:
        """Calculate marginal contribution to risk (MCTR) for each asset."""
        
        decomp = self.decompose_portfolio_risk(
            portfolio_weights, asset_returns, factor_names
        )
        
        total_var = decomp['total_variance']
        if total_var == 0:
            return {a: 0 for a in portfolio_weights}
        
        mctr = {}
        assets = list(portfolio_weights.keys())
        w = np.array([portfolio_weights[a] for a in assets])
        
        # Get covariance matrix of asset returns
        returns_matrix = np.column_stack([asset_returns[a] for a in assets])
        cov_matrix = np.cov(returns_matrix, rowvar=False)
        
        # MCTR = (w' * Sigma)_i / sqrt(w' * Sigma * w)
        portfolio_vol = np.sqrt(total_var)
        mctr_values = (cov_matrix @ w) / portfolio_vol
        
        for i, asset in enumerate(assets):
            mctr[asset] = float(mctr_values[i])
        
        return mctr
    
    def component_contribution_to_risk(
        self,
        portfolio_weights: Dict[str, float],
        asset_returns: Dict[str, np.ndarray]
    ) -> Dict[str, float]:
        """Calculate component contribution to risk (CCTR = w_i * MCTR_i)."""
        
        mctr = self.marginal_contribution_to_risk(
            portfolio_weights, asset_returns
        )
        
        cctr = {}
        for asset, weight in portfolio_weights.items():
            cctr[asset] = float(weight * mctr.get(asset, 0))
        
        return cctr


class PCAFactorModel:
    """Principal Component Analysis for factor extraction."""
    
    def __init__(self, n_components: int = 5):
        self.n_components = n_components
        self.components_ = None
        self.explained_variance_ = None
        self.explained_variance_ratio_ = None
        self.mean_ = None
        self.fitted = False
    
    def fit(self, returns: np.ndarray):
        """Fit PCA to asset returns."""
        # Center the data
        self.mean_ = np.mean(returns, axis=0)
        X_centered = returns - self.mean_
        
        # SVD
        U, s, Vt = np.linalg.svd(X_centered, full_matrices=False)
        
        # Components
        self.components_ = Vt[:self.n_components]
        self.explained_variance_ = (s**2) / (returns.shape[0] - 1)
        self.explained_variance_ratio_ = self.explained_variance_ / np.sum(self.explained_variance_)
        
        self.fitted = True
        return self
    
    def transform(self, returns: np.ndarray) -> np.ndarray:
        """Transform returns to factor space."""
        if not self.fitted:
            raise ValueError("PCA not fitted")
        
        X_centered = returns - self.mean_
        return X_centered @ self.components_.T
    
    def get_factor_returns(self, returns: np.ndarray) -> np.ndarray:
        """Get factor returns (principal component time series)."""
        return self.transform(returns)
    
    def reconstruct(self, factor_scores: np.ndarray) -> np.ndarray:
        """Reconstruct returns from factor scores."""
        if not self.fitted:
            raise ValueError("PCA not fitted")
        return factor_scores @ self.components_ + self.mean_


class FactorMimickingPortfolio:
    """Create factor-mimicking portfolios."""
    
    def __init__(self, factor_engine: FactorModelEngine):
        self.factor_engine = factor_engine
    
    def create_mimicking_portfolio(
        self,
        factor_name: str,
        asset_returns: Dict[str, np.ndarray],
        asset_covariance: np.ndarray = None,
        target_exposure: float = 1.0
    ) -> Dict[str, float]:
        """Create portfolio that mimics a factor."""
        
        assets = list(asset_returns.keys())
        n_assets = len(assets)
        
        # Get factor returns
        factor_returns = self.factor_engine._factor_data.get(factor_name)
        if factor_returns is None:
            raise ValueError(f"Factor {factor_name} not found")
        
        # Prepare asset returns matrix
        returns_matrix = np.column_stack([asset_returns[a] for a in assets])
        
        # Covariance matrix
        if asset_covariance is None:
            asset_covariance = np.cov(returns_matrix, rowvar=False)
        
        # Cross-covariance with factor
        factor_cov = np.cov(returns_matrix.T, factor_returns, rowvar=False)[:-1, -1]
        
        # Mimicking portfolio weights: w = Sigma^(-1) * cov(r, f) / (w' * cov(r, f))
        try:
            w_unscaled = np.linalg.solve(asset_covariance, factor_cov)
        except np.linalg.LinAlgError:
            w_unscaled = np.linalg.pinv(asset_covariance) @ factor_cov
        
        # Scale to target exposure
        factor_exposure = w_unscaled @ factor_cov
        if factor_exposure > 0:
            w = w_unscaled * target_exposure / factor_exposure
        else:
            w = w_unscaled
        
        return {assets[i]: float(w[i]) for i in range(n_assets)}


def create_factor_engine() -> FactorModelEngine:
    """Create factor model engine instance."""
    return FactorModelEngine()

def create_risk_decomposition(engine: FactorModelEngine) -> RiskDecomposition:
    """Create risk decomposition instance."""
    return RiskDecomposition(engine)

def create_pca_factor_model(n_components: int = 5) -> PCAFactorModel:
    """Create PCA factor model."""
    return PCAFactorModel(n_components)

def create_factor_mimicking_portfolio(engine: FactorModelEngine) -> FactorMimickingPortfolio:
    """Create factor mimicking portfolio builder."""
    return FactorMimickingPortfolio(engine)