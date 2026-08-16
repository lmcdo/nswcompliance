#!/usr/bin/env python3
"""
Prioritize missing LEP images by:
1. Which LGA (Leichhardt first, then Ashfield, then Marrickville)
2. Which are Key Sites (most important for users)
3. Which are triggered by Planning Portal
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from pathlib import Path

# Priority clauses that users actually see (from frontend mapping)
HIGH_PRIORITY = {
    # Development standards
    '4.3C': {'type': 'Dev Standard', 'lga': 'All', 'page': 37},
    '4.4': {'type': 'Dev Standard', 'lga': 'All', 'page': 39},

    # Heritage
    '5.10': {'type': 'Heritage', 'lga': 'All', 'page': 50},

    # Environmental
    '6.1': {'type': 'Environmental', 'lga': 'All', 'page': 60, 'name': 'Acid sulfate soils'},
    '6.5': {'type': 'Environmental', 'lga': 'All', 'page': 62, 'name': 'Flood liable land'},
    '6.6': {'type': 'Environmental', 'lga': 'All', 'page': 63, 'name': 'Contaminated land'},

    # Key Sites - Leichhardt
    '6.21': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 78, 'name': '45 Lilyfield Rd, Rozelle'},
    '6.22': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 79, 'name': '140-160 Victoria Rd, Rozelle'},
    '6.23': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 79, 'name': '162-178 Victoria Rd, Rozelle'},
    '6.24': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 80, 'name': '23-67 Allen St, Leichhardt'},
    '6.26': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 82, 'name': 'Alice St, Lilyfield'},
    '6.29': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 84, 'name': '13-15 Victoria Rd, Rozelle'},
    '6.31': {'type': 'Key Site', 'lga': 'Leichhardt', 'page': 86, 'name': '10-28 Perry St, Lilyfield'},

    # Key Sites - Ashfield
    '6.19': {'type': 'Key Site', 'lga': 'Ashfield', 'page': 76, 'name': 'Station St, Ashfield'},
    '6.25': {'type': 'Key Site', 'lga': 'Ashfield', 'page': 81, 'name': '37-61 Grosvenor Cres, Summer Hill'},

    # Key Sites - Marrickville
    '6.27': {'type': 'Key Site', 'lga': 'Marrickville', 'page': 83, 'name': '550-582 Parramatta Rd, Petersham'},
    '6.32': {'type': 'Key Site', 'lga': 'Marrickville', 'page': 87, 'name': 'Special Entertainment Precinct'},
    '6.33': {'type': 'Key Site', 'lga': 'Marrickville', 'page': 87, 'name': '126-134 Parramatta Rd, Stanmore'},
    '6.34': {'type': 'Key Site', 'lga': 'Marrickville', 'page': 88, 'name': '8-12 Mitchell St, Enmore'},

    # Heritage areas
    '6.20': {'type': 'Heritage Area', 'lga': 'All', 'page': 77, 'name': 'Heritage Conservation Areas'},
}

# Check existing images
pdf_pages_dir = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\frontend-nextjs\public\pdf-pages")
existing_images = set()
if pdf_pages_dir.exists():
    for img in pdf_pages_dir.glob("iwlep_*.png"):
        stem = img.stem
        # Extract clause from various patterns
        if 'clause_4_3C' in stem:
            existing_images.add('4.3C')
        elif 'clause_4_4' in stem:
            existing_images.add('4.4')
        elif 'clause_5_10' in stem:
            existing_images.add('5.10')
        elif 'clause_6_' in stem:
            parts = stem.split('_')
            for i, part in enumerate(parts):
                if part == 'clause' and i+2 < len(parts):
                    clause = f"{parts[i+1]}.{parts[i+2]}"
                    existing_images.add(clause)
                    break

print('=' * 90)
print('MISSING LEP IMAGES - PRIORITIZED BY LGA')
print('=' * 90)
print()
print('Priority: Leichhardt → Ashfield → Marrickville → All LGAs')
print()

# Organize by LGA in priority order
lga_order = ['Leichhardt', 'Ashfield', 'Marrickville', 'All']
by_lga = {lga: [] for lga in lga_order}

for clause, info in HIGH_PRIORITY.items():
    lga = info['lga']
    has_img = clause in existing_images
    by_lga[lga].append({
        'clause': clause,
        'info': info,
        'has_img': has_img
    })

# Print by LGA
for lga in lga_order:
    items = by_lga[lga]
    if len(items) == 0:
        continue

    missing = [i for i in items if not i['has_img']]
    has_img = [i for i in items if i['has_img']]

    print(f'\n{lga.upper()}')
    print('-' * 90)
    print(f'Total: {len(items)} | Has Image: {len(has_img)} | Missing: {len(missing)}')

    if len(missing) > 0:
        print(f'\n  ❌ MISSING ({len(missing)} to extract):')
        for item in sorted(missing, key=lambda x: x['clause']):
            clause = item['clause']
            info = item['info']
            name = info.get('name', info['type'])
            print(f'     Clause {clause:6s} (Page {info["page"]:2d}) - {info["type"]:15s} - {name}')

    if len(has_img) > 0:
        print(f'\n  ✅ HAS IMAGE ({len(has_img)}):')
        for item in sorted(has_img, key=lambda x: x['clause']):
            clause = item['clause']
            info = item['info']
            name = info.get('name', info['type'])
            print(f'     Clause {clause:6s} (Page {info["page"]:2d}) - {name}')

# Summary
print()
print('=' * 90)
print('EXTRACTION PLAN')
print('=' * 90)
print()

total_high_priority = len(HIGH_PRIORITY)
total_has = sum(1 for c in HIGH_PRIORITY if c in existing_images)
total_missing = total_high_priority - total_has

print(f'High-priority clauses:     {total_high_priority}')
print(f'Has PDF image:             {total_has} ({total_has/total_high_priority*100:.0f}%)')
print(f'Missing (need to extract): {total_missing} ({total_missing/total_high_priority*100:.0f}%)')
print()

# Print extraction order
print('RECOMMENDED EXTRACTION ORDER:')
print()

extraction_order = []
for lga in lga_order:
    for item in by_lga[lga]:
        if not item['has_img']:
            extraction_order.append(item)

if len(extraction_order) > 0:
    for i, item in enumerate(extraction_order, 1):
        clause = item['clause']
        info = item['info']
        name = info.get('name', info['type'])
        lga = info['lga']
        print(f'{i:2d}. Clause {clause:6s} (Page {info["page"]:2d}) - {lga:12s} - {name}')
else:
    print('✅ All high-priority clauses have images!')

print()
print(f'Total pages to extract: {len(extraction_order)}')
print(f'Estimated size: ~{len(extraction_order) * 200}KB ({len(extraction_order) * 0.2:.1f}MB)')
