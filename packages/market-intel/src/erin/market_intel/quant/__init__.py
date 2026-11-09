"""ERIN Market Intelligence - Quantitative Finance Module."""

from erin.market_intel.quant.distributions import (
    DistributionEngine,
    DistributionType,
    DistributionParams,
    DistributionFit,
    GARCHModel,
    create_distribution_engine,
    create_garch_model
)

from erin.market_intel.quant.monte_carlo import (
    MonteCarloEngine,
    MonteCarloModel,
    QuasiRandomType,
    MCConfig,
    MCResult,
    VarianceReduction,
    create_monte_carlo_engine
)

from erin.market_intel.quant.factor_models import (
    FactorModelEngine,
    FactorModelType,
    RegressionMethod,
    FactorModelConfig,
    FactorRegressionResult,
    FactorExposure,
    RiskDecomposition,
    PCAFactorModel,
    FactorMimickingPortfolio,
    create_factor_engine,
    create_risk_decomposition,
    create_pca_factor_model,
    create_factor_mimicking_portfolio
)

from erin.market_intel.quant.optimization import (
    OptimizationEngine,
    OptimizationMethod,
    RiskMeasure,
    OptimizationConfig,
    OptimizationResult,
    RebalancingOptimizer,
    create_optimization_engine,
    create_rebalancing_optimizer
)

__all__ = [
    # Distributions
    "DistributionEngine",
    "DistributionType",
    "DistributionParams",
    "DistributionFit",
    "GARCHModel",
    "create_distribution_engine",
    "create_garch_model",
    
    # Monte Carlo
    "MonteCarloEngine",
    "MonteCarloModel",
    "QuasiRandomType",
    "MCConfig",
    "MCResult",
    "VarianceReduction",
    "create_monte_carlo_engine",
    
    # Factor Models
    "FactorModelEngine",
    "FactorModelType",
    "RegressionMethod",
    "FactorModelConfig",
    "FactorRegressionResult",
    "FactorExposure",
    "RiskDecomposition",
    "PCAFactorModel",
    "FactorMimickingPortfolio",
    "create_factor_engine",
    "create_risk_decomposition",
    "create_pca_factor_model",
    "create_factor_mimicking_portfolio",
    
    # Optimization
    "OptimizationEngine",
    "OptimizationMethod",
    "RiskMeasure",
    "OptimizationConfig",
    "OptimizationResult",
    "RebalancingOptimizer",
    "create_optimization_engine",
    "create_rebalancing_optimizer",
]