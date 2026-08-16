#!/usr/bin/env python3
import requests
import json

# Test address in Newtown Special Entertainment Precinct (SEP - Clause 6.32)
addresses = [
    "101 King Street, Newtown NSW 2042",
    "200 King Street, Newtown NSW 2042",
    "150 King Street, Newtown NSW 2042",
]

for address in addresses:
    print("=" * 80)
    print(f"Testing: {address}")
    print("=" * 80)

    response = requests.get(f"http://localhost:3003/api/property?address={address}")
    d = response.json()

    if not d.get('success'):
        print("API FAILED")
        continue

    print(f"PropId: {d.get('data', {}).get('propId')}")
    print(f"Address returned: {d.get('data', {}).get('address')}")

    c = d.get('data', {}).get('constraints', {})
    print(f"Zone: {c.get('zone')}")
    print(f"LGA: {c.get('lga')}")

    lp_count = len(c.get('localProvisions', []))
    print(f"LocalProvisions: {lp_count}")

    if lp_count > 0:
        print("\nFOUND LOCAL PROVISIONS:")
        for lp in c.get('localProvisions', []):
            print(f"  - {lp.get('title')}")
            print(f"    Clause: {lp.get('clauseNumber')}, MapType: {lp.get('mapType')}, Page: {lp.get('pageNumber')}")
    else:
        print("\nNO LOCAL PROVISIONS")

    print()
