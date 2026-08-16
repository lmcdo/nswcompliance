#!/usr/bin/env python3
import requests
import json

response = requests.get("http://localhost:3003/api/property?address=10 Lackey Street, Ashfield NSW 2131")
d = response.json()

print("API Response:")
print(f"Success: {d.get('success')}")
print(f"PropId: {d.get('data', {}).get('propId')}")
print(f"Address returned: {d.get('data', {}).get('address')}")
print()

c = d.get('data', {}).get('constraints', {})
print("Constraints:")
print(f"  Zone: {c.get('zone')}")
print(f"  LGA: {c.get('lga')}")
print(f"  Heritage: {c.get('heritage')}")
print(f"  LocalProvisions: {len(c.get('localProvisions', []))}")
print()

if c.get('localProvisions'):
    print("Local Provisions:")
    for lp in c.get('localProvisions', []):
        print(f"  - {lp.get('title')}")
        print(f"    Clause: {lp.get('clauseNumber')}, MapType: {lp.get('mapType')}, Page: {lp.get('pageNumber')}")
else:
    print("NO LOCAL PROVISIONS RETURNED")
    print()
    print("Full constraints object:")
    print(json.dumps(c, indent=2))
