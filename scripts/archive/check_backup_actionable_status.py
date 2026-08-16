#!/usr/bin/env python3
"""Check v2_is_actionable status in backups"""

import json

backups = [
    ('Nov 22 (before v2)', '../backups/regulatory_provisions_before_v2_20251122_231205.json'),
    ('Nov 24 (4-layer complete)', '../backups/regulatory_provisions_4layer_complete_20251124_081014.json'),
]

for name, path in backups:
    print('=' * 70)
    print(f'{name}')
    print('=' * 70)

    try:
        with open(path, 'r') as f:
            backup = json.load(f)

        data = backup.get('data', [])
        print(f'Total provisions: {len(data):,}')

        if data:
            # Sample first 5
            print('\nSample provisions:')
            for i, prov in enumerate(data[:5]):
                actionable = prov.get('v2_is_actionable')
                text = (prov.get('provision_text') or '')[:60]
                print(f'  {i+1}. actionable={actionable} | "{text}..."')

            # Count
            true_count = sum(1 for p in data if p.get('v2_is_actionable') == True)
            false_count = sum(1 for p in data if p.get('v2_is_actionable') == False)
            null_count = sum(1 for p in data if p.get('v2_is_actionable') is None)

            print(f'\nActionable breakdown:')
            print(f'  True:  {true_count:,}')
            print(f'  False: {false_count:,}')
            print(f'  Null:  {null_count:,}')

    except Exception as e:
        print(f'ERROR: {e}')

    print()
