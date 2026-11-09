import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

from erin.market_intel.ai import ToolRegistry
registry = ToolRegistry()
tools = registry.list_tools()
print(len(tools))
for t in tools:
    print(f"  - {t.name}")
print('AI imports working!')