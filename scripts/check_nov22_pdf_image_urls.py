#!/usr/bin/env python3
"""Check if Nov 22 backup had pdf_page_image_url populated for SEPP provisions."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json

print('=' * 70)
print('CHECKING NOV 22 BACKUP: pdf_page_image_url for SEPP Provisions')
print('=' * 70)
print()

backup_file = 'backups/regulatory_provisions_before_v2_20251122_231205.json'

print(f'Loading: {backup_file}')
with open(backup_file, 'r', encoding='utf-8') as f:
    backup = json.load(f)

data = backup['data']

print(f'Total provisions: {len(data):,}')
print()

# Filter SEPP provisions
sepp_provisions = [
    p for p in data
    if 'State_Environmental_Planning_Policy' in p.get('document_id', '')
    or 'SEPP' in p.get('document_id', '')
]

print(f'SEPP provisions: {len(sepp_provisions):,}')
print()

# Check pdf_page_image_url coverage
has_url = sum(1 for p in sepp_provisions if p.get('pdf_page_image_url'))
no_url = len(sepp_provisions) - has_url

print('pdf_page_image_url coverage in Nov 22 backup:')
print(f'  Has pdf_page_image_url: {has_url:,} ({has_url/len(sepp_provisions)*100:.1f}%)')
print(f'  NULL pdf_page_image_url: {no_url:,} ({no_url/len(sepp_provisions)*100:.1f}%)')
print()

# Sample URLs
samples_with_url = [p for p in sepp_provisions if p.get('pdf_page_image_url')][:5]
samples_without_url = [p for p in sepp_provisions if not p.get('pdf_page_image_url')][:5]

if samples_with_url:
    print('Sample provisions WITH pdf_page_image_url:')
    for p in samples_with_url:
        print(f'  ID {p["id"]}: {p.get("document_id", "")[:60]}')
        print(f'    URL: {p["pdf_page_image_url"][:80]}...')
    print()

if samples_without_url:
    print('Sample provisions WITHOUT pdf_page_image_url:')
    for p in samples_without_url:
        print(f'  ID {p["id"]}: {p.get("document_id", "")[:60]}')
        print(f'    pdf_page: {p.get("pdf_page")}')
    print()

print('=' * 70)
print('CONCLUSION')
print('=' * 70)
print()

if has_url > 0:
    print(f'✅  Nov 22 backup HAD {has_url:,} SEPP provisions with pdf_page_image_url')
    print(f'   Current database has 0 SEPP provisions with pdf_page_image_url')
    print()
    print(f'⚠️  DATA LOSS: pdf_page_image_url was populated before Jan 27')
    print(f'   Something in the restore process lost this field')
else:
    print(f'❌  Nov 22 backup also had NULL pdf_page_image_url')
    print(f'   This was ALWAYS missing - not a recent data loss')
    print()
    print(f'   User must be mistaken about PDF links working before,')
    print(f'   OR there was a different mechanism showing PDFs')
