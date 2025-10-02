#!/usr/bin/env python3
"""Test the updated API with permission status"""
import requests
import json

# Test the API endpoint
url = "http://localhost:3007/api/compliance/constraints"

test_cases = [
    {
        "name": "Dwelling House in R2 (should be complying)",
        "payload": {
            "address": "30 Illawarra Road Marrickville",
            "zone": "R2",
            "lga": "Inner West",
            "developmentType": "dwelling_house"
        }
    },
    {
        "name": "General development in E3 (should be exempt)",
        "payload": {
            "address": "Test Address",
            "zone": "E3",
            "lga": "Test",
            "developmentType": "general"
        }
    },
    {
        "name": "Dual occupancy in R1 (should be complying)",
        "payload": {
            "address": "Test Address",
            "zone": "R1",
            "lga": "Test",
            "developmentType": "dual_occupancy"
        }
    }
]

print("=" * 80)
print("TESTING PERMISSION STATUS API")
print("=" * 80)

for test in test_cases:
    print(f"\n{test['name']}")
    print("-" * 80)

    try:
        response = requests.post(url, json=test['payload'], timeout=5)

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                permission_status = data.get('data', {}).get('permission_status')
                metadata = data.get('metadata', {})

                print(f"[OK] API Response Successful")
                print(f"  Zone: {metadata.get('zone')}")
                print(f"  Development Type: {metadata.get('developmentType')}")
                print(f"  Permission Status: {permission_status}")

                if permission_status:
                    print(f"  Result: {permission_status.upper()}")
                else:
                    print(f"  [WARN] No permission status returned")
            else:
                print(f"[ERROR] API returned failure: {data.get('error')}")
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to {url}")
        print(f"  Make sure Next.js dev server is running: cd frontend-nextjs && npm run dev")
        break
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out")
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
