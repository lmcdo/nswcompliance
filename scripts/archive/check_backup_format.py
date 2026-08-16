#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json

with open('backups/regulatory_provisions_before_v2_20251122_231205.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Keys:', list(data.keys()))

if 'data' in data:
    print('Data type:', type(data['data']))
    print('Data length:', len(data['data']))
    if data['data']:
        print('First item type:', type(data['data'][0]))
        print('First item keys:', list(data['data'][0].keys())[:15])
        print()
        print('Sample provision:')
        sample = data['data'][0]
        print(f"  ID: {sample.get('id')}")
        print(f"  pdf_page: {sample.get('pdf_page')}")
        print(f"  document_id: {sample.get('document_id')}")
