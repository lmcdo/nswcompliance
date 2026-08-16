#!/usr/bin/env python3
import sys, json, urllib.request
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://localhost:3003/api/property?address=185+Parramatta+Road+Annandale+NSW+2038"
resp = urllib.request.urlopen(url)
data = json.loads(resp.read())

print("Top-level keys:", list(data.keys()))
data = data.get('data', data)
print("Data keys:", list(data.keys()))
print()
constraints = data.get('constraints', {})
print("Constraints keys:", list(constraints.keys()) if constraints else "EMPTY")
print()

provisions = constraints.get('localProvisions', [])
print(f"Total local provisions: {len(provisions)}")
for p in provisions:
    print(f"  Clause {p.get('clauseNumber')} | nearby={p.get('isNearby')} | page={p.get('pageNumber')} | {p.get('title', '')[:70]}")

# Check if localProvisions is nested differently
if 'localProvisions' not in constraints:
    print("\nlocalProvisions not at top level, searching nested...")
    print(json.dumps(constraints, indent=2)[:2000])

# Also show raw Planning Portal layer
layers = data.get('planningLayers', [])
for layer in layers:
    if layer.get('layerName') == 'Key Sites Map':
        print(f"\n--- Planning Portal KSM raw ---")
        for r in layer.get('results', []):
            print(f"  Label: {r.get('Label')} | Legislative Clause: {r.get('Legislative Clause')}")
