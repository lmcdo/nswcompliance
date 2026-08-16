#!/usr/bin/env python3
"""
Investigate: Were NULL pdf_page provisions always NULL, or did they lose their pages recently?

Strategy:
1. Check the Nov 22 backup (before restore)
2. Check the Jan 28 enriched backup (after restore)
3. Compare pdf_page coverage for same provision IDs
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json
import os

BACKUP_DIR = 'backups'

# Find available backups
backups = [
    ('Nov 22 (pre-restore)', 'regulatory_provisions_before_v2_20251122_231205.json'),
    ('Jan 28 (enriched)', 'regulatory_provisions_enriched_20260128_093944.json'),
]

print('=' * 70)
print('INVESTIGATING: When did pdf_page go NULL?')
print('=' * 70)
print()

results = {}

for name, filename in backups:
    filepath = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(filepath):
        print(f'⚠️  {name}: File not found - {filename}')
        print()
        continue

    print(f'Loading {name}: {filename}')

    with open(filepath, 'r', encoding='utf-8') as f:
        backup = json.load(f)

    # Handle different backup formats
    if isinstance(backup, dict) and 'data' in backup:
        data = backup['data']
    elif isinstance(backup, list):
        data = backup
    else:
        print(f'  ⚠️  Unknown backup format')
        print()
        continue

    total = len(data)
    has_page = sum(1 for p in data if p.get('pdf_page') is not None)
    null_page = total - has_page

    # Check document sources
    doc_ids = {}
    for p in data:
        if p.get('pdf_page') is None:
            doc_id = p.get('document_id', 'unknown')
            doc_ids[doc_id] = doc_ids.get(doc_id, 0) + 1

    results[name] = {
        'total': total,
        'has_page': has_page,
        'null_page': null_page,
        'pct_null': null_page / total * 100 if total > 0 else 0,
        'null_by_doc': doc_ids
    }

    print(f'  Total provisions: {total:,}')
    print(f'  Has pdf_page: {has_page:,} ({has_page/total*100:.1f}%)')
    print(f'  NULL pdf_page: {null_page:,} ({null_page/total*100:.1f}%)')
    print()

print('=' * 70)
print('COMPARISON')
print('=' * 70)
print()

if len(results) >= 2:
    print('NULL pdf_page over time:')
    for name, data in results.items():
        print(f'  {name:30} {data["null_page"]:6,} NULL ({data["pct_null"]:5.1f}%)')
    print()

    # Check if it's the same documents
    print('Top documents with NULL pdf_page (Nov 22 backup):')
    if 'Nov 22 (pre-restore)' in results:
        nov_docs = results['Nov 22 (pre-restore)']['null_by_doc']
        for doc, count in sorted(nov_docs.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f'  {doc[:60]:60} {count:5,}')
    print()

print('=' * 70)
print('CONCLUSION')
print('=' * 70)
print()

if len(results) >= 2:
    nov_null = results.get('Nov 22 (pre-restore)', {}).get('pct_null', 0)
    jan_null = results.get('Jan 28 (enriched)', {}).get('pct_null', 0)

    if abs(nov_null - jan_null) < 5:
        print('✅ NULL pdf_page percentage is SIMILAR across backups')
        print(f'   Nov 22: {nov_null:.1f}% NULL')
        print(f'   Jan 28: {jan_null:.1f}% NULL')
        print()
        print('→ These provisions were ALWAYS missing pdf_page')
        print('→ NOT a recent data loss issue')
        print('→ Likely due to different extraction method for SEPP legislation')
    else:
        print('⚠️  NULL pdf_page percentage CHANGED significantly')
        print(f'   Nov 22: {nov_null:.1f}% NULL')
        print(f'   Jan 28: {jan_null:.1f}% NULL')
        print(f'   Change: {jan_null - nov_null:+.1f}%')
        print()
        print('→ Some provisions LOST their pdf_page values')
        print('→ Data quality issue from restore/migration')
