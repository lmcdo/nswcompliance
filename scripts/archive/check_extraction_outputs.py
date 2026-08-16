#!/usr/bin/env python3
"""Check what's in the extraction_outputs folder."""
import json
import os

output_dir = 'extraction_outputs'

for filename in os.listdir(output_dir):
    if not filename.endswith('.json'):
        continue
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        reqs = data.get('requirements', [])
        if not reqs:
            print(f'{filename}: No requirements')
            continue

        categories = {}
        has_source_id = 0
        for r in reqs:
            cat = r.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
            if r.get('source_provision_id'):
                has_source_id += 1

        print(f'\n{filename}:')
        print(f'  Total requirements: {len(reqs)}')
        print(f'  Has source_provision_id: {has_source_id}')
        print(f'  Categories:')
        for cat, cnt in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            print(f'    {cat}: {cnt}')

    except Exception as e:
        print(f'{filename}: {e}')
