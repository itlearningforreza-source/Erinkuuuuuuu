import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

from erin.market_intel.ai import ToolRegistry, AIAssistant

registry = ToolRegistry()
tools = registry.list_tools()
print(f'Registered tools: {len(tools)}')
for t in registry.list_tools():
    print(f'  - {t.name} (sensitivity: {t.sensitivity.value})')

assistant = AIAssistant()
print(f'AI Assistant created successfully')

print('AI Module integration working!')