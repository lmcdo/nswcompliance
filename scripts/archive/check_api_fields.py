#!/usr/bin/env python3
"""Check what fields the NSW Planning Portal layerintersect API returns for Land Zoning Map."""
import requests
import json

# 10 Bay St Botany - need to find propId first
search_url = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=10%20Bay%20St%20Botany"
r = requests.get(search_url, timeout=10)
results = r.json()
if results:
    prop_id = results[0].get('propId') or results[0].get('id')
    print(f"Property ID: {prop_id}")
else:
    print("No property found")
    exit(1)

# Get layerintersect
url = f"https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id={prop_id}&layers=epi"
r = requests.get(url, timeout=15)
data = r.json()

for layer in data:
    name = layer.get('layerName', '?')
    results = layer.get('results', [])
    if name == 'Land Zoning Map' and results:
        print(f"\n=== {name} ===")
        for k, v in results[0].items():
            val_str = str(v)[:200] if v else str(v)
            print(f"  {k}: {val_str}")
