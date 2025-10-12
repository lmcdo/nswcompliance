#!/usr/bin/env python3
"""Check what metadata is available in JSON extraction files"""

import json
from pathlib import Path

json_path = Path('output/Marrickville DCP 2011 - 4.1 Low Density Residential Development/auto/Marrickville DCP 2011 - 4.1 Low Density Residential Development_content_list.json')
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*80)
print("JSON METADATA ANALYSIS")
print("="*80)

# Sample first few items of different types
print("\nTEXT ELEMENT EXAMPLE:")
for item in data[:50]:
    if item.get('type') == 'text':
        print(f"Keys: {list(item.keys())}")
        print(f"Metadata: {json.dumps({k: item[k] for k in item.keys() if k != 'text'}, indent=2)}")
        break

print("\n\nTABLE ELEMENT EXAMPLE:")
for item in data[:200]:
    if item.get('type') == 'table':
        print(f"Keys: {list(item.keys())}")
        print(f"Metadata: {json.dumps({k: str(item[k])[:100] if k == 'table_body' else item[k] for k in item.keys() if k != 'table_body'}, indent=2)}")
        break

print("\n\nIMAGE ELEMENT EXAMPLE:")
for item in data[:200]:
    if item.get('type') == 'image':
        print(f"Keys: {list(item.keys())}")
        print(f"Metadata: {json.dumps({k: item[k] for k in item.keys()}, indent=2)}")
        break

# Count by type
from collections import Counter
types = Counter(item.get('type') for item in data)
print(f"\n\nELEMENT TYPE COUNTS:")
for typ, count in types.items():
    print(f"  {typ}: {count}")
