#!/usr/bin/env python3
"""Test DCP API endpoint"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

print("="*80)
print("DCP API ENDPOINT TESTS")
print("="*80)

base_url = "http://localhost:3007/api/dcp/full-text"

# Test 1: Search for setback controls
print("\n[TEST 1] Fetch setback controls")
response = requests.post(base_url, json={
    'documentId': 'Inner_West_Ashfield_DCP_2016___Chapter_F___Development_Category_with_IWLEP_2022_amendment',
    'category': 'setback'
}, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data['success']:
        count = data['metadata']['count']
        print(f"✓ Found {count} setback provisions")
        if data['data']['provisions']:
            prov = data['data']['provisions'][0]
            print(f"  Sample: {prov['ref_number']}")
            print(f"  Text: {prov['provision_text'][:150]}...")
    else:
        print(f"✗ API error: {data.get('error')}")
else:
    print(f"✗ HTTP {response.status_code}")

# Test 2: Search by control number
print("\n[TEST 2] Fetch specific control DS2.2")
response = requests.post(base_url, json={
    'documentId': 'Inner_West_Ashfield_DCP_2016___Chapter_F___Development_Category_with_IWLEP_2022_amendment',
    'controlNumber': 'DS2.2'
}, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data['success']:
        count = data['metadata']['count']
        print(f"✓ Found {count} provisions for DS2.2")
        if data['data']['provisions']:
            prov = data['data']['provisions'][0]
            print(f"  Control: {prov['ref_number']}")
            print(f"  Text: {prov['provision_text'][:200]}...")
    else:
        print(f"✗ API error: {data.get('error')}")
else:
    print(f"✗ HTTP {response.status_code}")

# Test 3: Search for parking controls
print("\n[TEST 3] Fetch car parking controls")
response = requests.post(base_url, json={
    'documentId': 'Inner_West_Ashfield_DCP_2016___Chapter_F___Development_Category_with_IWLEP_2022_amendment',
    'category': 'parking'
}, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data['success']:
        count = data['metadata']['count']
        print(f"✓ Found {count} parking provisions")
        if count > 0:
            # Show first 3
            for prov in data['data']['provisions'][:3]:
                print(f"  - {prov['ref_number']}: {prov['provision_text'][:100]}...")
    else:
        print(f"✗ API error: {data.get('error')}")
else:
    print(f"✗ HTTP {response.status_code}")

print("\n" + "="*80)
print("TESTS COMPLETE")
print("="*80)