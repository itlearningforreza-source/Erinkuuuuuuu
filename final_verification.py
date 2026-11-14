#!/usr/bin/env python3
"""Final comprehensive verification for ERIN 2.0 release - Import check only."""
import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

def test_all():
    print("=" * 60)
    print("ERIN 2.0 RELEASE VERIFICATION - IMPORT CHECK")
    print("=" * 60)
    
    modules = [
        # Data Infrastructure
        ("erin.data_infra.storage.sqlite", "SQLiteStorage"),
        ("erin.data_infra.storage.duckdb", "DuckDBStorage"),
        ("erin.data_infra.storage.lancedb", "LanceDBVectorStorage"),
        
        # Adapters
        ("erin.market_intel.adapters.base", "MarketDataProvider"),
        ("erin.market_intel.adapters.registry", "ProviderRegistry"),
        ("erin.market_intel.adapters.yfinance", "YFinanceProvider"),
        ("erin.market_intel.adapters.openbb", "OpenBBProvider"),
        ("erin.market_intel.adapters.fred", "FREDProvider"),
        ("erin.market_intel.adapters.alpha_vantage", "AlphaVantageProvider"),
        ("erin.market_intel.adapters.sec_edgar", "SECEdgarProvider"),
        
        # Domain
        ("erin.market_intel.domain.instrument_master", "InstrumentMaster"),
        ("erin.market_intel.domain.interfaces", "InstrumentId"),
        
        # Application Services
        ("erin.market_intel.application.market_data_service", "MarketDataService"),
        ("erin.market_intel.application.watchlist_service", "WatchlistService"),
        ("erin.market_intel.application.portfolio_service", "PortfolioService"),
        
        # Fundamental
        ("erin.market_intel.fundamental.company_service", "CompanyService"),
        ("erin.market_intel.fundamental.financial_statements_service", "FinancialStatementsService"),
        ("erin.market_intel.fundamental.ratio_engine", "RatioEngine"),
        ("erin.market_intel.fundamental.peer_group", "PeerGroupService"),
        ("erin.market_intel.fundamental.notebook_service", "NotebookService"),
        
        # Quantitative
        ("erin.market_intel.quant.distributions", "DistributionEngine"),
        ("erin.market_intel.quant.monte_carlo", "MonteCarloEngine"),
        ("erin.market_intel.quant.factor_models", "FactorModelEngine"),
        ("erin.market_intel.quant.optimization", "OptimizationEngine"),
        
        # Portfolio & Risk
        ("erin.market_intel.portfolio.domain", "Portfolio"),
        ("erin.market_intel.risk.var_engine", "VaREngine"),
        
        # Fixed Income & Derivatives
        ("erin.market_intel.fixed_income.bond_pricing", "BondPricingEngine"),
        ("erin.market_intel.derivatives.option_pricing", "OptionPricingEngine"),
        
        # Trading
        ("erin.market_intel.trading.oms", "OrderManagementSystem"),
        ("erin.market_intel.trading.backtest", "BacktestEngine"),
        ("erin.market_intel.trading.tca", "TCACalculator"),
        
        # Macro & News
        ("erin.market_intel.macro.calendar", "EconomicCalendar"),
        ("erin.market_intel.macro.news_pipeline", "NewsPipeline"),
        
        # AI
        ("erin.market_intel.ai.assistant", "ResearchAssistant"),
        ("erin.market_intel.ai.tools", "get_tool_registry"),
        ("erin.market_intel.ai.rag", "RAGPipeline"),
        
        # Security
        ("erin.market_intel.security.audit", "AuditLogger"),
        ("erin.market_intel.security.crypto", "KeyManager"),
        ("erin.market_intel.security.auth", "AuthManager"),
        ("erin.market_intel.security.hardening", "SystemHardening"),
        
        # Performance
        ("erin.market_intel.performance.caching", "CacheManager"),
        ("erin.market_intel.performance.connection_pool", "PoolManager"),
        ("erin.market_intel.performance.profiling", "Profiler"),
        ("erin.market_intel.performance.load_testing", "LoadTester"),
        ("erin.market_intel.performance.optimization", "QueryOptimizer"),
        ("erin.market_intel.performance.scaling", "ScalingManager"),
        ("erin.market_intel.performance.monitoring", "MetricsCollector"),
        
        # Deployment
        ("erin.market_intel.deployment.config", "DeploymentConfig"),
        ("erin.market_intel.deployment.health", "HealthChecker"),
        ("erin.market_intel.deployment.lifecycle", "LifecycleManager"),
        ("erin.market_intel.deployment.migrations", "MigrationManager"),
        ("erin.market_intel.deployment.backup", "BackupManager"),
        ("erin.market_intel.deployment.logging", "StructuredLogger"),
        ("erin.market_intel.deployment.observability", "ObservabilityStack"),
        ("erin.market_intel.deployment.release", "ReleaseManager"),
        
        # API
        ("erin.market_intel.api.main", "create_app"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {module_name}.{class_name} - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ ALL MODULES VERIFIED - READY FOR RELEASE")
        return True
    else:
        print(f"\n❌ {failed} MODULES FAILED")
        return False

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)