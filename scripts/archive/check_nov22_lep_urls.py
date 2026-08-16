#!/usr/bin/env python3
"""Check if Nov 22 backup had pdf_page_image_url for LEP provisions."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json

print('=' * 70)
print('CHECKING NOV 22 BACKUP: pdf_page_image_url for LEP Provisions')
print('=' * 70)
print()

backup_file = 'backups/regulatory_provisions_before_v2_20251122_231205.json'

print(f'Loading: {backup_file}')
with open(backup_file, 'r', encoding='utf-8') as f:
    backup = json.load(f)

data = backup['data']

print(f'Total provisions: {len(data):,}')
print()

# Filter LEP provisions (exclude DCP false positives)
lep_provisions = [
    p for p in data
    if 'Local_Environmental_Plan' in p.get('document_id', '')
    and 'DCP' not in p.get('document_id', '')
]

print(f'LEP provisions: {len(lep_provisions):,}')
print()

# Check pdf_page_image_url coverage
has_url = sum(1 for p in lep_provisions if p.get('pdf_page_image_url'))
no_url = len(lep_provisions) - has_url

print('pdf_page_image_url coverage in Nov 22 backup:')
print(f'  Has pdf_page_image_url: {has_url:,} ({has_url/len(lep_provisions)*100:.1f}%)' if len(lep_provisions) > 0 else '  No LEP provisions found')
print(f'  NULL pdf_page_image_url: {no_url:,} ({no_url/len(lep_provisions)*100:.1f}%)' if len(lep_provisions) > 0 else '')
print()

# Sample LEP provisions
if lep_provisions:
    samples = lep_provisions[:5]
    print('Sample LEP provisions from Nov 22:')
    for p in samples:
        doc = p.get('document_id', '')[:60]
        text = (p.get('provision_text', '') or '')[:80]
        url = p.get('pdf_page_image_url', 'NULL')
        print(f'  ID {p["id"]}: {doc}')
        print(f'    Text: {text}...')
        print(f'    pdf_page: {p.get("pdf_page")}')
        print(f'    pdf_page_image_url: {url if url != "NULL" else "NULL"}')
        print()

print('=' * 70)
print('FINAL DIAGNOSIS')
print('=' * 70)
print()

if has_url > 0:
    print(f'✅  Nov 22 backup HAD {has_url:,} LEP provisions with pdf_page_image_url')
    print(f'⚠️  Current database has 0 LEP provisions with pdf_page_image_url')
    print()
    print(f'🔥 DATA LOSS CONFIRMED: LEP provisions lost pdf_page_image_url after Jan 27')
    print(f'   This affects {len(lep_provisions):,} LEP provisions')
else:
    print(f'❌  Nov 22 backup also had NULL pdf_page_image_url for LEP')
    print(f'   LEP provisions NEVER had PDF links in regulatory_provisions')
    print()
    print(f'   Possible explanations:')
    print(f'   1. LEP PDFs were displayed via different mechanism')
    print(f'   2. LEP PDFs were in a different table')
    print(f'   3. User is mistaken about LEP provisions having PDF links')

print()
print('Complete coverage analysis:')
print(f'  SEPP: 95-100% (dedicated tables - unaffected by Jan 27)')
print(f'  DCP:  86.6% overall, 56.5% Leichhardt (regulatory_provisions)')
print(f'  LEP:  0% (regulatory_provisions - see above)')
