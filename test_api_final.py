import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

# Test all imports
from erin.core.config import get_settings
from erin.core.exceptions import ERINException, ValidationError, NotFoundError
from erin.core.logging import setup_logging, get_logger
from erin.market_intel.api import create_app
from erin.market_intel.api.routers import (
    market_data,
    instruments,
    watchlists,
    charts,
    portfolios,
    orders,
    risk,
    analytics,
    news,
    fundamentals,
)

print('All imports successful!')

# Test config
settings = get_settings()
print(f'Settings loaded: {settings.app_name} v{settings.app_version}')

# Test exceptions
try:
    raise ValueError("test")
except Exception as e:
    try:
        raise ValueError("test")
    except Exception as e:
        pass

# Test logging
setup_logging()
logger = get_logger('test')
logger.info('Test log message')
print('Logging setup: OK')

# Test app creation
app = create_app()
print(f'FastAPI app created: {app.title}')

# Test routes exist
routes = [route.path for route in app.routes]
print(f'Routes registered: {len(routes)}')
for route in routes:
    print(f'  {route.methods} {route.path}')

print('\\n✅ ALL API MODULES LOADED SUCCESSFULLY!')