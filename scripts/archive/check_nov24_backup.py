#!/usr/bin/env python3
import json

with open('../backups/regulatory_provisions_4layer_complete_20251124_081014.json', 'r') as f:
    backup = json.load(f)

print('Nov 24 backup structure:')
print(f'  Type: {type(backup).__name__}')

if isinstance(backup, dict):
    print(f'  Keys: {list(backup.keys())}')
    data = backup.get('data', backup)
elif isinstance(backup, list):
    data = backup
    print(f'  List with {len(backup)} items')
else:
    data = []

if data and len(data) > 0:
    print(f'\nTotal provisions: {len(data):,}')
    print(f'\nFirst provision keys: {list(data[0].keys())[:15]}')
    print(f'\nFirst 5 v2_is_actionable values:')
    for i, prov in enumerate(data[:5]):
        actionable = prov.get('v2_is_actionable')
        text = (prov.get('provision_text') or '')[:60]
        print(f'  {i+1}. {actionable} | "{text}..."')

    true_count = sum(1 for p in data if p.get('v2_is_actionable') == True)
    false_count = sum(1 for p in data if p.get('v2_is_actionable') == False)
    null_count = sum(1 for p in data if p.get('v2_is_actionable') is None)

    print(f'\nActionable counts:')
    print(f'  True:  {true_count:,}')
    print(f'  False: {false_count:,}')
    print(f'  Null:  {null_count:,}')
