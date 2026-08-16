#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check pdf_page status in November 22, 2025 backup
"""
import json, sys, io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("Loading November 22, 2025 backup...")
with open('backups/regulatory_provisions_before_v2_20251122_231205.json', 'r') as f:
    data = json.load(f)
    if isinstance(data, dict):
        records = data.get('data', [])
    else:
        records = data

print(f"Total records in backup: {len(records):,}\n")

# Filter Leichhardt provisions
leichhardt = [r for r in records if 'Leichhardt' in r.get('document_id', '')]
print(f"Leichhardt provisions: {len(leichhardt):,}")

# Check pdf_page distribution
null_pages = sum(1 for r in leichhardt if r.get('pdf_page') is None)
has_pages = sum(1 for r in leichhardt if r.get('pdf_page') is not None)

print(f"\npdf_page status:")
print(f"  NULL: {null_pages:,} ({null_pages/len(leichhardt)*100:.1f}%)")
print(f"  Has value: {has_pages:,} ({has_pages/len(leichhardt)*100:.1f}%)")

# Check by layer
generic_leich = [r for r in leichhardt if r.get('v2_dcp_layer') == 'generic']
print(f"\nGeneric layer provisions: {len(generic_leich):,}")

generic_null_pages = sum(1 for r in generic_leich if r.get('pdf_page') is None)
generic_has_pages = sum(1 for r in generic_leich if r.get('pdf_page') is not None)

print(f"  NULL pdf_page: {generic_null_pages:,} ({generic_null_pages/len(generic_leich)*100:.1f}%)")
print(f"  Has pdf_page: {generic_has_pages:,} ({generic_has_pages/len(generic_leich)*100:.1f}%)")

# Check Part C Section 1
part_c1 = [r for r in generic_leich if r.get('v2_dcp_part') and 'Part C Section 1' in r.get('v2_dcp_part', '')]
print(f"\nPart C Section 1 (generic): {len(part_c1):,}")

if part_c1:
    c1_null = sum(1 for r in part_c1 if r.get('pdf_page') is None)
    c1_has = sum(1 for r in part_c1 if r.get('pdf_page') is not None)
    print(f"  NULL pdf_page: {c1_null:,} ({c1_null/len(part_c1)*100:.1f}%)")
    print(f"  Has pdf_page: {c1_has:,} ({c1_has/len(part_c1)*100:.1f}%)")

# Sample records
print(f"\nSample Part C Section 1 records (first 10):")
for i, r in enumerate(part_c1[:10], 1):
    page = r.get('pdf_page')
    page_str = str(page) if page is not None else 'NULL'
    print(f"  {i}. ID={r.get('id')}, Page={page_str}, Text={r.get('provision_text', '')[:60]}...")

print(f"\n{'='*80}")
print("CONCLUSION")
print("="*80)

if generic_null_pages > len(generic_leich) * 0.5:
    print(f"\n🔴 BACKUP ALREADY HAD NULL PAGES")
    print(f"   November 22 backup: {generic_null_pages:,} / {len(generic_leich):,} NULL ({generic_null_pages/len(generic_leich)*100:.1f}%)")
    print(f"   Current database: 1,036 / 1,554 NULL (67%)")
    print(f"\n   The backup already had NULL pdf_page values")
    print(f"   Re-enrichment did NOT create this problem")
elif c1_null > len(part_c1) * 0.5:
    print(f"\n🔴 PART C SECTION 1 HAD NULL PAGES IN BACKUP")
    print(f"   This explains the missing provisions")
else:
    print(f"\n✅ Backup had pdf_page populated")
    print(f"   Re-enrichment may have set them to NULL")
