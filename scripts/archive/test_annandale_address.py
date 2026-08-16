#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

address = "185 Parramatta Road, Annandale NSW 2038"

print("=" * 80)
print(f"Testing: {address}")
print("=" * 80)
print()

response = requests.get(f"http://localhost:3003/api/property?address={address}")
d = response.json()

if not d.get('success'):
    print("API FAILED:", d.get('error'))
    sys.exit(1)

data = d.get('data', {})
print(f"PropId: {data.get('propId')}")
print(f"Address returned: {data.get('address')}")
print()

c = data.get('constraints', {})
print("CONSTRAINTS:")
print(f"  Zone: {c.get('zone')}")
print(f"  LGA: {c.get('lga')}")
print(f"  Heritage: {c.get('heritage')}")
print(f"  Precinct: {c.get('precinctId')}")
print()

lp = c.get('localProvisions', [])
print(f"LOCAL PROVISIONS: {len(lp)}")
print()

if lp:
    for i, prov in enumerate(lp, 1):
        print(f"{i}. {prov.get('title', 'No title')}")
        print(f"   Clause: {prov.get('clauseNumber', 'N/A')}")
        print(f"   MapType: {prov.get('mapType', 'N/A')}")
        print(f"   Page: {prov.get('pageNumber', 'N/A')}")
        print(f"   Class: {prov.get('class', 'N/A')}")
        print(f"   isNearby: {prov.get('isNearby', False)}")
        print()

    # Check if any are KSM
    ksm_provisions = [p for p in lp if p.get('mapType') in ['KSM', 'Key Sites Map']]
    if ksm_provisions:
        print(f"KEY SITES MAP PROVISIONS: {len(ksm_provisions)}")
        for p in ksm_provisions:
            clause = p.get('clauseNumber')
            page = p.get('pageNumber')

            # Test if R2 image exists
            if clause and page:
                image_url = f"https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/iwlep_clause_{clause.replace('.', '_')}_page_{page}.png"
                print(f"  Clause {clause} (Page {page})")
                print(f"  Image URL: {image_url}")

                # Check if image is accessible
                img_response = requests.head(image_url, timeout=5)
                if img_response.status_code == 200:
                    print(f"  Image: ACCESSIBLE")
                else:
                    print(f"  Image: NOT FOUND (HTTP {img_response.status_code})")
else:
    print("NO LOCAL PROVISIONS RETURNED")
