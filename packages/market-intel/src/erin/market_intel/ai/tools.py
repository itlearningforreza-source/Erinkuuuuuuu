"""AI Tools - Allowlisted tools for AI assistant with sandbox execution."""

import asyncio
import logging
import json
import hashlib
import subprocess
import tempfile
import os
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Any, Callable
from enum import Enum
from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    pass

from erin.market_intel.quant.optimization import OptimizationEngine, OptimizationMethod, OptimizationConfig
from erin.market_intel.risk import VaREngine, VaRMethod, VaRConfig
from erin.market_intel.quant.monte_carlo import MonteCarloEngine, MCConfig, MonteCarloModel
from erin.market_intel.quant.factor_models import FactorModelEngine, FactorModelConfig, FactorModelType
from erin.market_intel.macro import EconomicCalendar, NLPProcessor
from erin.market_intel.trading.backtest import EventDrivenBacktester, BacktestConfig, BacktestMode
from erin.data_infra.storage.sqlite import get_sqlite_storage

logger = logging.getLogger(__name__)


class ToolSensitivity(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SandboxProfile(str, Enum):
    PYTHON_BASIC = "PYTHON_BASIC"
    PYTHON_DATA = "PYTHON_DATA"  # numpy, pandas, scipy
    PYTHON_FULL = "PYTHON_FULL"
    FINANCIAL_COMPUTE = "FINANCIAL_COMPUTE"
    SQL_READ = "SQL_READ"
    HTTP_GET = "HTTP_GET"


@dataclass
class ToolDefinition:
    """AI tool definition."""
    name: str
    version: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    read_only: bool = True
    sensitivity: ToolSensitivity = ToolSensitivity.READ_ONLY
    allowed_roles: List[str] = field(default_factory=lambda: ["analyst", "researcher", "trader", "admin"])
    rate_limit: Optional[str] = None  # e.g., "10/minute"
    timeout_seconds: int = 30
    sandbox_profile: SandboxProfile = SandboxProfile.PYTHON_BASIC
    is_active: bool = True


@dataclass
class ToolCall:
    """AI tool invocation."""
    id: str = field(default_factory=lambda: hashlib.md5(f"{datetime.utcnow()}".encode()).hexdigest()[:16])
    session_id: str = ""
    user_id: str = ""
    tool_name: str = ""
    tool_version: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Optional[Dict[str, Any]] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, REJECTED
    sensitivity: ToolSensitivity = ToolSensitivity.READ_ONLY
    approval_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time_ms: int = 0
    error: Optional[str] = None
    hash_chain: str = ""  # For audit trail
    
    def to_audit_record(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status,
            "sensitivity": self.sensitivity.value,
            "approval_id": self.approval_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "hash_chain": self.hash_chain
        }


class ToolRegistry:
    """Registry of available AI tools."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default financial tools."""
        
        # Market data tools
        self.register(ToolDefinition(
            name="get_market_data",
            version="1.0",
            description="Get real-time or historical market data for symbols",
            input_schema={
                "type": "object",
                "properties": {
                    "symbols": {"type": "array", "items": {"type": "string"}},
                    "fields": {"type": "array", "items": {"type": "string"}, "default": ["price", "change", "volume"]},
                    "provider": {"type": "string", "default": "openbb"}
                },
                "required": ["symbols"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "object"}
                }
            },
            sensitivity=ToolSensitivity.READ_ONLY,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=10
        ))
        
        # Fundamental data
        self.register(ToolDefinition(
            name="get_fundamental_data",
            version="1.0",
            description="Get fundamental data (financial statements, ratios) for a company",
            input_schema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "statement_type": {"type": "string", "enum": ["income", "balance", "cashflow", "all"]},
                    "period": {"type": "string", "enum": ["annual", "quarterly", "ttm"]},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["ticker"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.READ_ONLY,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=15
        ))
        
        # Technical indicators
        self.register(ToolDefinition(
            name="calculate_technical_indicators",
            version="1.0",
            description="Calculate technical indicators for a symbol",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "indicators": {"type": "array", "items": {"type": "string"}},
                    "period": {"type": "integer", "default": 14},
                    "timeframe": {"type": "string", "enum": ["1d", "1h", "5m"], "default": "1d"}
                },
                "required": ["symbol"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.READ_ONLY,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=10
        ))
        
        # Risk metrics
        self.register(ToolDefinition(
            name="calculate_var",
            version="1.0",
            description="Calculate Value at Risk for a portfolio",
            input_schema={
                "type": "object",
                "properties": {
                    "positions": {"type": "object", "additionalProperties": {"type": "number"}},
                    "method": {"type": "string", "enum": ["historical", "parametric", "monte_carlo", "cornish_fisher"]},
                    "confidence": {"type": "number", "minimum": 0.9, "maximum": 0.999, "default": 0.95},
                    "horizon_days": {"type": "integer", "default": 1},
                    "portfolio_value": {"type": "number", "default": 1000000}
                },
                "required": ["positions"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.FINANCIAL_COMPUTE,
            timeout_seconds=30
        ))
        
        # Stress testing
        self.register(ToolDefinition(
            name="run_stress_test",
            version="1.0",
            description="Run portfolio stress test scenarios",
            input_schema={
                "type": "object",
                "properties": {
                    "positions": {"type": "object", "additionalProperties": {"type": "number"}},
                    "scenario": {"type": "string", "enum": ["2008_crisis", "2020_covid", "1987_crash", "rate_shock", "credit_spread", "custom"]},
                    "custom_shocks": {"type": "object", "additionalProperties": {"type": "number"}},
                    "portfolio_value": {"type": "number", "default": 1000000}
                },
                "required": ["positions"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.FINANCIAL_COMPUTE,
            timeout_seconds=30
        ))
        
        # Portfolio optimization
        self.register(ToolDefinition(
            name="optimize_portfolio",
            version="1.0",
            description="Optimize portfolio weights using various methods",
            input_schema={
                "type": "object",
                "properties": {
                    "symbols": {"type": "array", "items": {"type": "string"}},
                    "method": {"type": "string", "enum": ["max_sharpe", "min_variance", "risk_parity", "hrp", "max_diversification", "black_litterman"]},
                    "target_return": {"type": "number"},
                    "target_risk": {"type": "number"},
                    "risk_aversion": {"type": "number", "default": 1.0},
                    "constraints": {
                        "type": "object",
                        "properties": {
                            "long_only": {"type": "boolean", "default": True},
                            "max_weight": {"type": "number", "default": 0.3},
                            "min_weight": {"type": "number", "default": 0.0},
                            "max_turnover": {"type": "number"},
                            "sector_caps": {"type": "object"}
                        }
                    },
                    "risk_free_rate": {"type": "number", "default": 0.02}
                },
                "required": ["symbols"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.FINANCIAL_COMPUTE,
            timeout_seconds=60
        ))
        
        # Backtesting
        self.register(ToolDefinition(
            name="run_backtest",
            version="1.0",
            description="Run backtest for a trading strategy",
            input_schema={
                "type": "object",
                "properties": {
                    "strategy": {"type": "string", "description": "Strategy code or name"},
                    "symbols": {"type": "array", "items": {"type": "string"}},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "initial_capital": {"type": "number", "default": 1000000},
                    "commission_bps": {"type": "number", "default": 5},
                    "slippage_bps": {"type": "number", "default": 2}
                },
                "required": ["strategy", "symbols", "start_date", "end_date"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.FINANCIAL_COMPUTE,
            timeout_seconds=120
        ))
        
        # Monte Carlo simulation
        self.register(ToolDefinition(
            name="run_monte_carlo",
            version="1.0",
            description="Run Monte Carlo simulation for option pricing or portfolio projection",
            input_schema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "enum": ["gbm", "gbm_jump", "heston", "cir", "vasicek", "sabr"]},
                    "parameters": {"type": "object"},
                    "n_paths": {"type": "integer", "default": 10000},
                    "n_steps": {"type": "integer", "default": 252},
                    "time_horizon": {"type": "number", "default": 1.0}
                },
                "required": ["model", "parameters"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=60
        ))
        
        # Factor analysis
        self.register(ToolDefinition(
            name="run_factor_analysis",
            version="1.0",
            description="Run factor model analysis (FF3, FF5, Carhart, PCA)",
            input_schema={
                "type": "object",
                "properties": {
                    "symbols": {"type": "array", "items": {"type": "string"}},
                    "model_type": {"type": "string", "enum": ["capm", "ff3", "ff5", "carhart4", "pca", "custom"]},
                    "period": {"type": "string", "enum": ["1m", "3m", "6m", "1y", "3y", "5y"], "default": "1y"},
                    "benchmark": {"type": "string", "default": "SPY"}
                },
                "required": ["symbols"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.FINANCIAL_COMPUTE,
            timeout_seconds=30
        ))
        
        # Economic calendar
        self.register(ToolDefinition(
            name="get_economic_calendar",
            version="1.0",
            description="Get upcoming economic events and releases",
            input_schema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "countries": {"type": "array", "items": {"type": "string"}},
                    "importance": {"type": "array", "items": {"type": "string"}},
                    "categories": {"type": "array", "items": {"type": "string"}}
                }
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.READ_ONLY,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=15
        ))
        
        # News search
        self.register(ToolDefinition(
            name="search_news",
            version="1.0",
            description="Search financial news articles",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tickers": {"type": "array", "items": {"type": "string"}},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "limit": {"type": "integer", "default": 20}
                }
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.READ_ONLY,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=15
        ))
        
        # NLP analysis
        self.register(ToolDefinition(
            name="analyze_text",
            version="1.0",
            description="Analyze text for sentiment, entities, tickers, and classification",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "extract_tickers": {"type": "boolean", "default": True},
                    "classify": {"type": "boolean", "default": True},
                    "sentiment": {"type": "boolean", "default": True},
                    "entities": {"type": "boolean", "default": True}
                },
                "required": ["text"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.READ_ONLY,
            sandbox_profile=SandboxProfile.PYTHON_DATA,
            timeout_seconds=15
        ))
        
        # Python code execution (sandboxed)
        self.register(ToolDefinition(
            name="execute_python",
            version="1.0",
            description="Execute Python code in sandboxed environment",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "libraries": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "default": 30}
                },
                "required": ["code"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.HIGH,
            sandbox_profile=SandboxProfile.PYTHON_FULL,
            timeout_seconds=60,
            allowed_roles=["researcher", "trader", "admin"]
        ))
        
        # SQL query (read-only)
        self.register(ToolDefinition(
            name="query_database",
            version="1.0",
            description="Execute read-only SQL query on market database",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "params": {"type": "object"},
                    "limit": {"type": "integer", "default": 1000}
                },
                "required": ["query"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.SQL_READ,
            timeout_seconds=30,
            allowed_roles=["analyst", "researcher", "trader", "admin"]
        ))
        
        # HTTP request (for external APIs)
        self.register(ToolDefinition(
            name="http_request",
            version="1.0",
            description="Make HTTP GET request to external API",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
                    "headers": {"type": "object"},
                    "params": {"type": "object"},
                    "timeout": {"type": "integer", "default": 30}
                },
                "required": ["url"]
            },
            output_schema={"type": "object"},
            sensitivity=ToolSensitivity.MEDIUM,
            sandbox_profile=SandboxProfile.HTTP_GET,
            timeout_seconds=30,
            allowed_roles=["researcher", "trader", "admin"]
        ))
    
    def register(self, tool: ToolDefinition):
        self._tools[f"{tool.name}@{tool.version}"] = tool
    
    def get_tool(self, name: str, version: str = "1.0") -> Optional[ToolDefinition]:
        return self._tools.get(f"{name}@{version}")
    
    def list_tools(self, role: str = None, sensitivity: ToolSensitivity = None) -> List[ToolDefinition]:
        tools = list(self._tools.values())
        if role:
            tools = [t for t in tools if role in t.allowed_roles]
        if sensitivity:
            tools = [t for t in tools if t.sensitivity == sensitivity]
        return tools
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM function calling."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema
            }
            for t in self._tools.values() if t.is_active
        ]


class ToolExecutor:
    """Execute AI tools with sandboxing and audit."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._pending_approvals: Dict[str, ToolCall] = {}
    
    async def execute(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        session_id: str,
        user_id: str,
        tool_version: str = "1.0"
    ) -> ToolCall:
        """Execute a tool with full audit trail."""
        import time
        
        tool = self.registry.get_tool(tool_name, tool_version)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}@{tool_version}")
        
        if not tool.is_active:
            raise ValueError(f"Tool not active: {tool_name}")
        
        # Create tool call record
        call = ToolCall(
            session_id=session_id,
            user_id=user_id,
            tool_name=tool_name,
            tool_version=tool_version,
            inputs=inputs,
            sensitivity=tool.sensitivity
        )
        
        # Check if approval needed
        if tool.sensitivity in [ToolSensitivity.HIGH, ToolSensitivity.CRITICAL]:
            call.status = "PENDING_APPROVAL"
            self._pending_approvals[call.id] = call
            return call
        
        # Execute
        call.status = "RUNNING"
        start_time = time.time()
        
        try:
            output = await self._execute_tool(tool, inputs)
            call.outputs = output
            call.status = "COMPLETED"
        except Exception as e:
            call.status = "FAILED"
            call.error = str(e)
            logger.error(f"Tool execution failed: {tool_name}: {e}")
        finally:
            call.completed_at = datetime.utcnow()
            call.execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Store audit record
        self._store_audit(call)
        
        return call
    
    async def _execute_tool(self, tool: ToolDefinition, inputs: Dict) -> Dict[str, Any]:
        """Execute specific tool implementation."""
        
        if tool.name == "get_market_data":
            return await self._get_market_data(inputs)
        elif tool.name == "get_fundamental_data":
            return await self._get_fundamental_data(inputs)
        elif tool.name == "calculate_technical_indicators":
            return await self._calculate_technical_indicators(inputs)
        elif tool.name == "calculate_var":
            return await self._calculate_var(inputs)
        elif tool.name == "run_stress_test":
            return await self._run_stress_test(inputs)
        elif tool.name == "optimize_portfolio":
            return await self._optimize_portfolio(inputs)
        elif tool.name == "run_backtest":
            return await self._run_backtest(inputs)
        elif tool.name == "run_monte_carlo":
            return await self._run_monte_carlo(inputs)
        elif tool.name == "run_factor_analysis":
            return await self._run_factor_analysis(inputs)
        elif tool.name == "get_economic_calendar":
            return await self._get_economic_calendar(inputs)
        elif tool.name == "search_news":
            return await self._search_news(inputs)
        elif tool.name == "analyze_text":
            return await self._analyze_text(inputs)
        elif tool.name == "execute_python":
            return await self._execute_python(inputs)
        elif tool.name == "query_database":
            return await self._query_database(inputs)
        elif tool.name == "http_request":
            return await self._http_request(inputs)
        else:
            raise ValueError(f"Tool not implemented: {tool.name}")
    
    async def _get_market_data(self, inputs: Dict) -> Dict:
        # Would integrate with market data service
        symbols = inputs.get("symbols", [])
        return {"data": {s: {"price": 100.0, "change": 0.5} for s in symbols}}
    
    async def _get_fundamental_data(self, inputs: Dict) -> Dict:
        return {"financials": [], "ratios": {}}
    
    async def _calculate_technical_indicators(self, inputs: Dict) -> Dict:
        return {"indicators": {}}
    
    async def _calculate_var(self, inputs: Dict) -> Dict:
        from erin.market_intel.risk import VaREngine, VaRMethod, VaRConfig
        from decimal import Decimal
        import numpy as np
        
        positions = inputs["positions"]
        method = VaRMethod(inputs.get("method", "historical"))
        confidence = Decimal(str(inputs.get("confidence", 0.95)))
        horizon = inputs.get("horizon_days", 1)
        portfolio_value = Decimal(str(inputs.get("portfolio_value", 1000000)))
        
        # Generate synthetic returns for demo
        symbols = list(positions.keys())
        returns = np.random.normal(0.0005, 0.01, (len(symbols), 252))
        
        # Weight by positions
        weights = np.array([positions[s] for s in symbols])
        weights = weights / weights.sum()
        portfolio_returns = returns.T @ weights
        
        var_engine = VaREngine()
        config = VaRConfig(method=method, confidence_level=confidence, horizon_days=horizon)
        var_val, es_val, details = var_engine.calculate_var(portfolio_returns, portfolio_value, config)
        
        return {
            "var": float(var_val),
            "es": float(es_val),
            "confidence": float(confidence),
            "horizon_days": horizon,
            "method": method.value,
            "details": details
        }
    
    async def _run_stress_test(self, inputs: Dict) -> Dict:
        from erin.market_intel.risk import StressTestingEngine
        
        engine = StressTestingEngine()
        positions = inputs["positions"]
        scenario = inputs.get("scenario", "2008_crisis")
        portfolio_value = Decimal(str(inputs.get("portfolio_value", 1000000)))
        
        # Mock portfolio returns
        symbols = list(positions.keys())
        portfolio_returns = {s: np.random.normal(0.0005, 0.01, 252) for s in symbols}
        weights = {s: positions[s] for s in symbols}
        
        result = engine.run_stress_test(portfolio_returns, weights, scenario, portfolio_value)
        
        return {
            "scenario": result.scenario.value,
            "portfolio_value": float(result.portfolio_value),
            "stressed_value": float(result.stressed_value),
            "pnl": float(result.pnl),
            "pnl_pct": float(result.pnl_pct)
        }
    
    async def _optimize_portfolio(self, inputs: Dict) -> Dict:
        from erin.market_intel.quant.optimization import OptimizationEngine, OptimizationMethod, OptimizationConfig
        import numpy as np
        
        symbols = inputs["symbols"]
        method = OptimizationMethod(inputs["method"])
        
        # Generate synthetic returns
        returns = np.random.normal(0.0005, 0.01, (len(symbols), 252))
        
        opt = OptimizationEngine()
        opt.set_data(returns.T, symbols)
        
        config = OptimizationConfig(method=method)
        result = opt.optimize(config)
        
        return {
            "weights": result.weights,
            "expected_return": result.expected_return,
            "expected_risk": result.expected_risk,
            "sharpe_ratio": result.sharpe_ratio
        }
    
    async def _run_backtest(self, inputs: Dict) -> Dict:
        # Simplified backtest
        return {"trades": [], "metrics": {}}
    
    async def _run_monte_carlo(self, inputs: Dict) -> Dict:
        from erin.market_intel.quant.monte_carlo import MonteCarloEngine, MCConfig, MonteCarloModel
        
        model = MonteCarloModel(inputs["model"])
        params = inputs["parameters"]
        
        config = MCConfig(
            model=model,
            n_paths=inputs.get("n_paths", 10000),
            n_steps=inputs.get("n_steps", 252),
            time_horizon=inputs.get("time_horizon", 1.0),
            params=params
        )
        
        engine = MonteCarloEngine()
        result = engine.run(config)
        
        return {
            "stats": result.stats,
            "runtime": result.runtime_seconds
        }
    
    async def _run_factor_analysis(self, inputs: Dict) -> Dict:
        from erin.market_intel.quant.factor_models import FactorModelEngine, FactorModelConfig, FactorModelType
        
        engine = FactorModelEngine()
        model_type = FactorModelType(inputs.get("model_type", "ff3"))
        
        # Would load real factor data
        config = FactorModelConfig(model_type=model_type)
        # engine.load_fama_french_factors(...)
        
        return {"betas": {}, "alpha": 0, "r_squared": 0}
    
    async def _get_economic_calendar(self, inputs: Dict) -> Dict:
        from erin.market_intel.macro import EconomicCalendar, FREDEconomicCalendarProvider
        from datetime import date, timedelta
        
        provider = FREDEconomicCalendarProvider()
        start = date.fromisoformat(inputs.get("start_date", date.today().isoformat()))
        end = date.fromisoformat(inputs.get("end_date", (date.today() + timedelta(days=30)).isoformat()))
        
        await provider.sync_calendar(start, end, inputs.get("countries"))
        events = provider.calendar.get_events()
        
        return {"events": [{"title": e.title, "date": e.scheduled_time.isoformat(), "importance": e.importance.value} for e in events]}
    
    async def _search_news(self, inputs: Dict) -> Dict:
        return {"articles": []}
    
    async def _analyze_text(self, inputs: Dict) -> Dict:
        from erin.market_intel.macro import NLPProcessor
        
        nlp = NLPProcessor()
        text = inputs["text"]
        
        result = {}
        if inputs.get("extract_tickers", True):
            result["tickers"] = await nlp.extract_tickers(text)
        if inputs.get("classify", True):
            result["categories"] = [c.value for c in await nlp.classify_category(text[:100], text[:500])]
        if inputs.get("sentiment", True):
            sentiment, score, conf = await nlp.analyze_sentiment(text)
            result["sentiment"] = sentiment.value
            result["sentiment_score"] = float(score)
            result["confidence"] = float(conf)
        if inputs.get("entities", True):
            result["entities"] = await nlp.extract_entities(text)
        
        return result
    
    async def _execute_python(self, inputs: Dict) -> Dict:
        """Execute Python code in sandbox."""
        code = inputs["code"]
        timeout = inputs.get("timeout", 30)
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run with restricted environment
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'PYTHONPATH': '/home/rezaahmadkhairuddin/ERIN/packages/market-intel/src'}
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timeout", "stdout": "", "stderr": "Timeout"}
        except Exception as e:
            return {"error": str(e), "stdout": "", "stderr": str(e)}
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    async def _query_database(self, inputs: Dict) -> Dict:
        from erin.data_infra.storage.sqlite import get_sqlite_storage
        
        sqlite = get_sqlite_storage()
        query = inputs["query"]
        params = inputs.get("params", ())
        limit = inputs.get("limit", 1000)
        
        rows = sqlite.fetch_all(query + f" LIMIT {limit}", params)
        return {"rows": [dict(r) for r in rows]}
    
    async def _http_request(self, inputs: Dict) -> Dict:
        import aiohttp
        
        url = inputs["url"]
        method = inputs.get("method", "GET")
        headers = inputs.get("headers", {})
        params = inputs.get("params", {})
        timeout = aiohttp.ClientTimeout(total=inputs.get("timeout", 30))
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, headers=headers, params=params) as resp:
                return {
                    "status": resp.status,
                    "data": await resp.json() if resp.content_type == "application/json" else await resp.text(),
                    "headers": dict(resp.headers)
                }
    
    def _store_audit(self, call: ToolCall):
        """Store audit record."""
        from erin.data_infra.storage.sqlite import get_sqlite_storage
        sqlite = get_sqlite_storage()
        
        record = call.to_audit_record()
        sqlite.execute(
            """INSERT INTO tool_calls (id, session_id, user_id, tool_name, tool_version, 
            inputs, outputs, status, sensitivity, approval_id, started_at, completed_at, 
            execution_time_ms, error, hash_chain)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record["id"], record["session_id"], record["user_id"], record["tool_name"],
             record["tool_version"], json.dumps(record["inputs"]), 
             json.dumps(record["outputs"]) if record["outputs"] else None,
             record["status"], record["sensitivity"], record["approval_id"],
             record["started_at"], record["completed_at"], record["execution_time_ms"],
             record["error"], record["hash_chain"])
        )


class ApprovalManager:
    """Manage tool call approvals."""
    
    def __init__(self, executor: ToolExecutor):
        self.executor = executor
        self._pending: Dict[str, ToolCall] = {}
    
    def request_approval(self, call: ToolCall) -> str:
        """Request approval for a tool call."""
        self._pending[call.id] = call
        return call.id
    
    def approve(self, call_id: str, approver_id: str) -> bool:
        """Approve a pending tool call."""
        call = self._pending.get(call_id)
        if not call or call.status != "PENDING_APPROVAL":
            return False
        
        call.approval_id = approver_id
        call.status = "APPROVED"
        
        # Execute asynchronously
        asyncio.create_task(self._execute_approved(call))
        return True
    
    def reject(self, call_id: str, reason: str) -> bool:
        """Reject a pending tool call."""
        call = self._pending.get(call_id)
        if not call or call.status != "PENDING_APPROVAL":
            return False
        
        call.status = "REJECTED"
        call.error = reason
        self.executor._store_audit(call)
        del self._pending[call_id]
        return True
    
    async def _execute_approved(self, call: ToolCall):
        """Execute an approved tool call."""
        tool = self.executor.registry.get_tool(call.tool_name, call.tool_version)
        if not tool:
            call.status = "FAILED"
            call.error = "Tool not found"
            self.executor._store_audit(call)
            return
        
        call.status = "RUNNING"
        start_time = time.time()
        
        try:
            output = await self.executor._execute_tool(tool, call.inputs)
            call.outputs = output
            call.status = "COMPLETED"
        except Exception as e:
            call.status = "FAILED"
            call.error = str(e)
        finally:
            call.completed_at = datetime.utcnow()
            call.execution_time_ms = int((time.time() - start_time) * 1000)
            self.executor._store_audit(call)
            self._pending.pop(call.id, None)
    
    def get_pending(self) -> List[ToolCall]:
        return list(self._pending.values())


def create_tool_registry() -> ToolRegistry:
    return ToolRegistry()


def create_tool_executor(registry: ToolRegistry = None) -> ToolExecutor:
    return ToolExecutor(registry or ToolRegistry())


def create_approval_manager(executor: ToolExecutor) -> ApprovalManager:
    return ApprovalManager(executor)