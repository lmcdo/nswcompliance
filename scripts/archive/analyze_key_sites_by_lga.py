#!/usr/bin/env python3
"""
Analyze Key Sites Map clauses by LGA area (Leichhardt, Ashfield, Marrickville).
Identify which PDFs are missing.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

# All Key Sites Map provisions from Inner West LEP 2022 Part 6
KEY_SITES = {
    '6.14': {'name': 'Site-specific provisions - Schedule 7', 'area': 'General', 'page': 73},
    '6.15': {'name': 'Development on land at 1 Llewellyn Street, Rhodes', 'area': 'Rhodes (former Auburn)', 'page': 73},
    '6.16': {'name': 'Development on land at 107-151 Llewellyn Street, Rhodes', 'area': 'Rhodes (former Auburn)', 'page': 74},
    '6.17': {'name': 'Development on land at 23-51 Bowden Street, Rhodes', 'area': 'Rhodes (former Auburn)', 'page': 75},
    '6.18': {'name': 'Development on land at 90 Gipps Street, Concord', 'area': 'Concord (former Canada Bay)', 'page': 76},
    '6.19': {'name': 'Development on land in Station Street, Ashfield', 'area': 'Ashfield', 'page': 76},
    '6.20': {'name': 'Heritage conservation areas', 'area': 'All LGAs', 'page': 77},
    '6.21': {'name': 'Development on land at 45 Lilyfield Road, Rozelle', 'area': 'Leichhardt', 'page': 78},
    '6.22': {'name': 'Development on land at 140-160 Victoria Road, Rozelle', 'area': 'Leichhardt', 'page': 79},
    '6.23': {'name': 'Development on land at 162-178 Victoria Road, Rozelle', 'area': 'Leichhardt', 'page': 79},
    '6.24': {'name': 'Development on land at 23-67 Allen Street, Leichhardt', 'area': 'Leichhardt', 'page': 80},
    '6.25': {'name': 'Development on land at 37-61 Grosvenor Crescent, Summer Hill', 'area': 'Ashfield (Summer Hill)', 'page': 81},
    '6.26': {'name': 'Development on land in Alice Street, Lilyfield', 'area': 'Leichhardt', 'page': 82},
    '6.27': {'name': 'Development on land at 550-582 Parramatta Road, Petersham', 'area': 'Marrickville', 'page': 83},
    '6.28': {'name': 'Development on land at 34 Bay Street, Ultimo', 'area': 'Former Sydney (not Inner West)', 'page': 84},
    '6.29': {'name': 'Development on land at 13-15 Victoria Road, Rozelle', 'area': 'Leichhardt', 'page': 84},
    '6.30': {'name': 'Development on land at 70-86 Bay Street, Ultimo', 'area': 'Former Sydney (not Inner West)', 'page': 85},
    '6.31': {'name': 'Development on land at 10-28 Perry Street, Lilyfield', 'area': 'Leichhardt', 'page': 86},
    '6.32': {'name': 'Special Entertainment Precinct Map', 'area': 'Newtown (Marrickville)', 'page': 87},
    '6.33': {'name': 'Development on land at 126-134 Parramatta Road, Stanmore', 'area': 'Marrickville', 'page': 87},
    '6.34': {'name': 'Development on land at 8-12 Mitchell Street, Enmore', 'area': 'Marrickville', 'page': 88},
}

# Check existing images
pdf_pages_dir = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\frontend-nextjs\public\pdf-pages")
existing_images = {}
if pdf_pages_dir.exists():
    for img in pdf_pages_dir.glob("iwlep_clause_*.png"):
        # Extract clause number from filename: iwlep_clause_6_14_page_73.png
        parts = img.stem.split('_')
        if len(parts) >= 4 and parts[0] == 'iwlep' and parts[1] == 'clause':
            clause = f"{parts[2]}.{parts[3]}"
            existing_images[clause] = img.name

print('=' * 90)
print('KEY SITES MAP PROVISIONS - IMAGE STATUS BY LGA')
print('=' * 90)
print()

# Group by LGA
lga_groups = {
    'Leichhardt': [],
    'Ashfield': [],
    'Marrickville': [],
    'Other': []
}

for clause, info in sorted(KEY_SITES.items()):
    area = info['area']
    if 'Leichhardt' in area or 'Rozelle' in area or 'Lilyfield' in area:
        lga_groups['Leichhardt'].append(clause)
    elif 'Ashfield' in area or 'Summer Hill' in area:
        lga_groups['Ashfield'].append(clause)
    elif 'Marrickville' in area or 'Petersham' in area or 'Newtown' in area or 'Stanmore' in area or 'Enmore' in area:
        lga_groups['Marrickville'].append(clause)
    else:
        lga_groups['Other'].append(clause)

# Print by LGA
for lga in ['Leichhardt', 'Ashfield', 'Marrickville', 'Other']:
    clauses = lga_groups[lga]
    if len(clauses) == 0:
        continue

    missing = [c for c in clauses if c not in existing_images]
    has_img = [c for c in clauses if c in existing_images]

    print(f'\n{lga.upper()}')
    print('-' * 90)
    print(f'Total: {len(clauses)} | Has Image: {len(has_img)} | Missing: {len(missing)}')
    print()

    for clause in sorted(clauses):
        info = KEY_SITES[clause]
        status = '✅' if clause in existing_images else '❌'
        img_name = existing_images.get(clause, 'MISSING')

        print(f'{status} Clause {clause:5s} | Page {info["page"]:2d} | {img_name:45s} | {info["name"][:50]}')

# Summary
print()
print('=' * 90)
print('SUMMARY')
print('=' * 90)
print()

total_key_sites = len(KEY_SITES)
total_has_img = len(existing_images)
total_missing = total_key_sites - total_has_img

print(f'Total Key Sites Map provisions:     {total_key_sites}')
print(f'Has PDF image:                      {total_has_img} ({total_has_img/total_key_sites*100:.0f}%)')
print(f'Missing PDF image:                  {total_missing} ({total_missing/total_key_sites*100:.0f}%)')
print()

# Show missing by LGA
print('Missing by LGA:')
for lga in ['Leichhardt', 'Ashfield', 'Marrickville', 'Other']:
    clauses = lga_groups[lga]
    missing = [c for c in clauses if c not in existing_images]
    if len(missing) > 0:
        print(f'  {lga:15s}: {len(missing)} missing - {", ".join(missing)}')

print()
print('=' * 90)
print('RECOMMENDED EXTRACTION ORDER')
print('=' * 90)
print()

# List missing in order requested: Leichhardt first, then Ashfield, then Marrickville
for lga in ['Leichhardt', 'Ashfield', 'Marrickville']:
    clauses = lga_groups[lga]
    missing = sorted([c for c in clauses if c not in existing_images])
    if len(missing) > 0:
        print(f'\n{lga} ({len(missing)} to extract):')
        for clause in missing:
            info = KEY_SITES[clause]
            print(f'  Clause {clause} (Page {info["page"]:2d}): {info["name"]}')
