#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if January 28 enriched backup has pdf_page populated
(This backup was created AFTER re-enrichment on Jan 28)
"""
import json, sys, io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\nChecking January 28 enriched backup...")
print("(Created AFTER re-enrichment at 12:25 AM)")

with open('backups/regulatory_provisions_enriched_20260128_002526.json', 'r') as f:
    data = json.load(f)
    if isinstance(data, dict):
        records = data.get('data', [])
    else:
        records = data

leichhardt = [r for r in records if 'Leichhardt' in r.get('document_id', '')]

print(f"\nLeichhardt provisions: {len(leichhardt):,}")

null_pages = sum(1 for r in leichhardt if r.get('pdf_page') is None)
has_pages = sum(1 for r in leichhardt if r.get('pdf_page') is not None)

print(f"  NULL pdf_page: {null_pages:,} ({null_pages/len(leichhardt)*100:.1f}%)")
print(f"  Has pdf_page: {has_pages:,} ({has_pages/len(leichhardt)*100:.1f}%)")

# Check if v2 columns exist
if leichhardt:
    has_v2 = 'v2_dcp_layer' in leichhardt[0]
    print(f"  Has v2 columns: {has_v2}")

print(f"\n{'='*80}")
if null_pages == 0:
    print("✅ This backup has ALL pdf_page values!")
    print("   Solution: This is already the good backup, database is fine")
elif null_pages < len(leichhardt) * 0.5:
    print("✅ This backup has MOST pdf_page values!")
    print(f"   Only {null_pages/len(leichhardt)*100:.1f}% are NULL")
    print("   Solution: Use this backup, it's better than Nov 22")
else:
    print("❌ This backup ALSO has NULL pdf_page issue")
    print(f"   {null_pages/len(leichhardt)*100:.1f}% are NULL")
    print("   This is the SAME as Nov 22 backup (inherited the problem)")
    print("   Need to reconstruct pdf_page from other sources")
