#!/usr/bin/env python3
"""Test all development types for E1 zone"""
import requests

url = "http://localhost:3007/api/compliance/constraints"

dev_types = [
    "dwelling_house",
    "secondary_dwelling",
    "dual_occupancy",
    "multi_dwelling",
    "shop_top_housing",
    "residential_flat",
    "boarding_house",
    "child_care",
    "commercial"
]

print("=" * 80)
print("E1 ZONE - ALL DEVELOPMENT TYPES")
print("Address: 333 Illawarra Road Marrickville")
print("=" * 80)

for dev_type in dev_types:
    payload = {
        "address": "333 Illawarra Road Marrickville",
        "zone": "E1",
        "lga": "Inner West",
        "developmentType": dev_type
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('data', {}).get('permission_status', 'unknown')
            print(f"{dev_type:25} → {status:15}")
        else:
            print(f"{dev_type:25} → ERROR {response.status_code}")
    except Exception as e:
        print(f"{dev_type:25} → ERROR: {e}")

print("=" * 80)
