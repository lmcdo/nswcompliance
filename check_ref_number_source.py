#!/usr/bin/env python3
"""Check where ref_numbers come from in JSON extraction"""

import json
from pathlib import Path

json_path = Path('output/Marrickville DCP 2011 - 4.1 Low Density Residential Development/auto/Marrickville DCP 2011 - 4.1 Low Density Residential Development_content_list.json')
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Look for text elements that contain our ref_numbers
search_terms = ['C8', '4.1.20.3', 'Historical development patterns', 'table in 4.1.6.2', 'Design solutions for additions']

print("Searching for ref_number sources in JSON extraction...")
print("="*80)

for idx, item in enumerate(data[:200]):  # Check first 200 items
    if item.get('type') == 'text':
        text = item.get('text', '')
        for term in search_terms:
            if term in text:
                print(f"\nItem #{idx}, Page {item.get('page_idx')}")
                print(f"Type: {item.get('category_type', 'unknown')}")
                print(f"Text: {text[:300]}")
                print("---")
                break

# Also check if tables have any ref info
print("\n" + "="*80)
print("Checking table elements...")
for idx, item in enumerate(data[:200]):
    if item.get('type') == 'table':
        print(f"\nTable #{idx}, Page {item.get('page_idx')}")
        table_caption = item.get('table_caption', '')
        if table_caption:
            print(f"Caption: {table_caption}")
        print(f"HTML preview: {item.get('table_body', '')[:200]}")
        print("---")
