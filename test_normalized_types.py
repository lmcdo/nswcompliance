#!/usr/bin/env python3
import requests

url = "http://localhost:3007/api/compliance/constraints"

test_cases = [
    ("E1", "dwelling_house", "prohibited"),
    ("E1", "secondary_dwelling", "prohibited"),  # Should normalize to dwelling_house
    ("E1", "multi_dwelling", "prohibited"),       # Should normalize to residential_flat_building
    ("R2", "dwelling_house", "permitted/complying"),
    ("R2", "secondary_dwelling", "permitted/complying"),
    ("R2", "multi_dwelling", "permitted/complying"),
]

print("=" * 80)
print("TESTING NORMALIZED DEVELOPMENT TYPES")
print("=" * 80)

for zone, dev_type, expected in test_cases:
    payload = {"zone": zone, "lga": "Test", "developmentType": dev_type}
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('data', {}).get('permission_status', 'unknown')
            result = "PASS" if expected in status or status in expected else "CHECK"
            print(f"{zone:5} + {dev_type:20} -> {status:15} (expected: {expected:20}) [{result}]")
        else:
            print(f"{zone:5} + {dev_type:20} -> ERROR {response.status_code}")
    except Exception as e:
        print(f"{zone:5} + {dev_type:20} -> ERROR: {e}")

print("=" * 80)
