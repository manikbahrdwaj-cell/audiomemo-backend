from langchain_core.runnables import RunnableConfig

r = RunnableConfig(configurable={'test': 'value', 'phone': '+1234'})
print(f'Type: {type(r)}')
print(f'Value: {r}')
print(f'Dict value: {dict(r)}')
print(f'Has configurable attr: {hasattr(r, "configurable")}')
if hasattr(r, 'configurable'):
    print(f'Attribute configurable: {r.configurable}')
print(f'Get configurable via key: {r.get("configurable") if isinstance(r, dict) else "not dict"}')
print(f'Dir: {[x for x in dir(r) if not x.startswith("_")]}')
print(f'Keys: {list(r.keys()) if hasattr(r, "keys") else "no keys"}')
