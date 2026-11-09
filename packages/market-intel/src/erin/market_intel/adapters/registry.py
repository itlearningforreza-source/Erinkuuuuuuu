"""Market Data Provider Registry - Central registry for all market data providers."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Type
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.market_intel.adapters.base import MarketDataProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Provider configuration."""
    provider_id: str
    name: str
    class_name: str
    module_path: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0


class ProviderRegistry:
    """Registry for managing market data providers."""
    
    def __init__(self):
        self._providers: Dict[str, 'MarketDataProvider'] = {}
        self._configs: Dict[str, ProviderConfig] = {}
        self._default_provider: Optional[str] = None
        self._initialized = False
    
    def register_provider(self, provider: 'MarketDataProvider', config: Dict[str, Any] = None) -> None:
        """Register a provider instance."""
        provider_id = provider.provider_id
        self._providers[provider_id] = provider
        logger.info(f"Registered provider: {provider_id}")
        
        if self._default_provider is None:
            self._default_provider = provider_id
    
    def register_config(self, config: Dict[str, Any]) -> None:
        """Register provider configuration for lazy loading."""
        provider_id = config.get("provider_id")
        if not provider_id:
            raise ValueError("provider_id is required")
        
        config_obj = ProviderConfig(
            provider_id=provider_id,
            name=config.get("name", provider_id),
            class_name=config.get("class_name"),
            module_path=config.get("module_path"),
            config=config.get("config", {}),
            enabled=config.get("enabled", True),
            priority=config.get("priority", 0)
        )
        
        self._configs[provider_id] = config_obj
        
        if config.get("set_default", False) or self._default_provider is None:
            self._default_provider = provider_id
    
    def get(self, provider_id: str) -> Optional['MarketDataProvider']:
        """Get provider by ID."""
        return self._providers.get(provider_id)
    
    def get_default(self) -> Optional['MarketDataProvider']:
        """Get default provider."""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        return next(iter(self._providers.values()), None)
    
    def list_providers(self) -> List[str]:
        """List all registered provider IDs."""
        return list(self._providers.keys())
    
    def get_enabled_providers(self) -> List['MarketDataProvider']:
        """Get all enabled providers."""
        return [p for p in self._providers.values() if p.requires_api_key() is not False]
    
    async def initialize_all(self):
        """Initialize all configured providers."""
        if self._initialized:
            return
        
        for provider_id, config in self._configs.items():
            if not config.enabled:
                continue
            
            if provider_id in self._providers:
                continue
            
            try:
                await self._load_provider(config)
            except Exception as e:
                logger.error(f"Failed to load provider {provider_id}: {e}")
        
        self._initialized = True
    
    async def _load_provider(self, config: 'ProviderConfig'):
        """Dynamically load provider class."""
        module = __import__(config.module_path, fromlist=[config.class_name])
        provider_class = getattr(module, config.class_name)
        
        provider = provider_class(**config.config)
        self._providers[config.provider_id] = provider
        
        if config.priority > 0 and (self._default_provider is None or config.priority > 0):
            self._default_provider = config.provider_id
        
        logger.info(f"Loaded provider: {config.provider_id}")
    
    def get_all(self) -> Dict[str, 'MarketDataProvider']:
        return self._providers.copy()
    
    def set_default(self, provider_id: str) -> bool:
        if provider_id in self._providers:
            self._default_provider = provider_id
            return True
        return False
    
    def get_default(self) -> Optional[str]:
        return self._default_provider
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for provider_id, provider in self._providers.items():
            try:
                results[provider_id] = await provider.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {provider_id}: {e}")
                results[provider_id] = False
        return results


# Global registry instance
provider_registry = ProviderRegistry()


# Default provider configurations
DEFAULT_PROVIDER_CONFIGS = [
    {
        "provider_id": "openbb",
        "name": "OpenBB Platform",
        "class_name": "OpenBBProvider",
        "module_path": "erin.market_intel.adapters.openbb",
        "config": {
            "api_base_url": "http://localhost:6900",
            "api_key": None,
            "timeout": 30
        },
        "enabled": True,
        "priority": 100,
        "set_default": True
    },
    {
        "provider_id": "yfinance",
        "name": "Yahoo Finance",
        "class_name": "YFinanceProvider",
        "module_path": "erin.market_intel.adapters.yfinance",
        "config": {
            "timeout": 30
        },
        "enabled": True,
        "priority": 50
    },
    {
        "provider_id": "fred",
        "name": "FRED (Federal Reserve Economic Data)",
        "class_name": "FREDProvider",
        "module_path": "erin.market_intel.adapters.fred",
        "config": {
            "api_key": None,
            "timeout": 30
        },
        "enabled": True,
        "priority": 50
    },
    {
        "provider_id": "alpha_vantage",
        "name": "Alpha Vantage",
        "class_name": "AlphaVantageProvider",
        "module_path": "erin.market_intel.adapters.alpha_vantage",
        "config": {
            "api_key": None,
            "timeout": 30
        },
        "enabled": True,
        "priority": 40
    },
    {
        "provider_id": "sec_edgar",
        "name": "SEC EDGAR",
        "class_name": "SECEdgarProvider",
        "module_path": "erin.market_intel.adapters.sec_edgar",
        "config": {
            "user_agent": "ERIN/2.0 (contact@erin.local)",
            "timeout": 30
        },
        "enabled": True,
        "priority": 30
    }
]


def initialize_provider_registry(config: Dict = None) -> ProviderRegistry:
    """Initialize provider registry with default or custom config."""
    registry = ProviderRegistry()
    
    configs = config.get("providers", DEFAULT_PROVIDER_CONFIGS) if config else DEFAULT_PROVIDER_CONFIGS
    
    for config in configs:
        registry.register_config(config)
    
    return registry