#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import requests

# Test address
address = "10 Lackey Street, Ashfield NSW 2131"

response = requests.get(f"http://localhost:3003/api/property?address={address}")
data = response.json()

lp = data.get('constraints', {}).get('localProvisions', [])
print(f'Address: {address}')
print(f'Local Provisions: {len(lp)}')
print()

if lp:
    for p in lp:
        print(f'  - {p.get("title", "No title")}')
        print(f'    Clause: {p.get("clauseNumber", "N/A")}')
        print(f'    MapType: {p.get("mapType", "N/A")}')
        print(f'    PageNumber: {p.get("pageNumber", "N/A")}')
        print(f'    isNearby: {p.get("isNearby", False)}')
        print()
else:
    print('  No local provisions found')
    print()
    print('Checking what we DID get:')
    print(f'  Zone: {data.get("constraints", {}).get("zone")}')
    print(f'  LGA: {data.get("constraints", {}).get("lga")}')
    print(f'  Heritage: {data.get("constraints", {}).get("heritage")}')
