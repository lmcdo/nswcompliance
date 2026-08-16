#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

address = "185 Parramatta Road, Annandale NSW 2038"

print("=" * 80)
print(f"FULL PLANNING PORTAL RESPONSE FOR: {address}")
print("=" * 80)
print()

response = requests.get(f"http://localhost:3003/api/property?address={address}")
data = response.json()

# Get the full planning layers
planning_layers = data.get('data', {}).get('planningLayers', [])

print(f"Total Planning Layers: {len(planning_layers)}")
print()

# Find Key Sites Map layer
for layer in planning_layers:
    layer_name = layer.get('layerName', '')
    if 'Key Sites' in layer_name or layer_name == 'Key Sites Map':
        print("FOUND KEY SITES MAP LAYER:")
        print(f"  Layer Name: {layer_name}")
        print(f"  Results: {len(layer.get('results', []))}")
        print()

        for i, result in enumerate(layer.get('results', []), 1):
            print(f"  Result {i}:")
            print(f"    Label: {result.get('Label', 'N/A')}")
            print(f"    Class: {result.get('Class', 'N/A')}")
            print(f"    Legislative Clause: {result.get('Legislative Clause', 'N/A')}")
            print(f"    EPI Name: {result.get('EPI Name', 'N/A')}")

            # Check all fields
            for key, value in result.items():
                if key not in ['Label', 'Class', 'Legislative Clause', 'EPI Name', 'layerName']:
                    print(f"    {key}: {value}")
            print()

print()
print("=" * 80)
print("LOCAL PROVISIONS RETURNED BY API:")
print("=" * 80)
print()

lp = data.get('data', {}).get('constraints', {}).get('localProvisions', [])
for i, prov in enumerate(lp, 1):
    print(f"{i}. {prov.get('title')}")
    print(f"   Clause: {prov.get('clauseNumber')}")
    print(f"   Page: {prov.get('pageNumber')}")
    print(f"   isNearby: {prov.get('isNearby')}")
    print()
