import json, sys

import os
p = os.path.expandvars(r"C:\Users\lawre\AppData\Local\Temp\da_results.json")
with open(p) as f:
    data = json.load(f)

print(f"Total: {data['TotalCount']}")
for a in data['Application'][:20]:
    loc = a.get('Location', [{}])[0]
    dev_types = [d['DevelopmentType'] for d in a.get('DevelopmentType', [])]
    addr = loc.get('FullAddress', 'NO ADDR')
    x = loc.get('X', '')
    y = loc.get('Y', '')
    det = a.get('DeterminationDate', '')[:10]
    print(f"{addr} | {det} | X={x} Y={y} | {dev_types}")
