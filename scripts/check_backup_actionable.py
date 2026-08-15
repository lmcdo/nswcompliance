#!/usr/bin/env python3
"""Check actionable classification in November backup"""

import json

# Check November backup
with open('backups/regulatory_provisions_before_v2_20251122_231205.json', 'r', encoding='utf-8') as f:
    backup = json.load(f)

data = backup.get('data', [])
print(f'November backup has {len(data)} provisions\n')

# Check actionable status
actionable_true = sum(1 for p in data if p.get('v2_is_actionable') == True)
actionable_false = sum(1 for p in data if p.get('v2_is_actionable') == False)
actionable_null = sum(1 for p in data if p.get('v2_is_actionable') is None)

print('Actionable classification in Nov 22 backup:')
print(f'  True: {actionable_true:,}')
print(f'  False: {actionable_false:,}')
print(f'  Null: {actionable_null:,}')

# Check what v2 columns exist
if data:
    sample = data[0]
    v2_columns = [k for k in sample.keys() if k.startswith('v2_')]
    print(f'\nv2_ columns in backup ({len(v2_columns)}):')
    for col in sorted(v2_columns):
        print(f'  - {col}')

# Sample some provisions that should be actionable
print('\nSample provisions from backup:')
for i, prov in enumerate(data[:5]):
    text = prov.get('provision_text', '')[:80]
    actionable = prov.get('v2_is_actionable')
    layer = prov.get('v2_dcp_layer')
    print(f'\n{i+1}. actionable={actionable}, layer={layer}')
    print(f'   "{text}..."')
