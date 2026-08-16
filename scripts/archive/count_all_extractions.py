#!/usr/bin/env python3
"""Count all extracted requirements with provision IDs."""
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

output_dir = 'extraction_outputs'
total = 0
categories = defaultdict(int)
provision_ids = set()

def process_file(filepath):
    global total
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('requirements', [])
        else:
            return

        for item in items:
            prov_id = item.get('primary_source_provision_id') or item.get('source_provision_id')
            cat = item.get('category', 'unknown')
            if prov_id:
                provision_ids.add(prov_id)
                categories[cat] += 1
                total += 1

    except Exception as e:
        print(f'Error in {filepath}: {e}')

# Process all JSON files recursively
for root, dirs, files in os.walk(output_dir):
    for filename in files:
        if filename.endswith('.json'):
            process_file(os.path.join(root, filename))

print("="*70)
print("ALL EXTRACTION DATA")
print("="*70)
print(f"\nTotal extracted requirements: {total}")
print(f"Unique provision IDs: {len(provision_ids)}")

print(f"\nCategories (top 20):")
for cat, cnt in sorted(categories.items(), key=lambda x: -x[1])[:20]:
    print(f"  {cat}: {cnt}")

# Save provision IDs for later use
with open('extraction_outputs/all_extracted_provision_ids.json', 'w') as f:
    json.dump(list(provision_ids), f)
print(f"\nSaved {len(provision_ids)} provision IDs to all_extracted_provision_ids.json")
