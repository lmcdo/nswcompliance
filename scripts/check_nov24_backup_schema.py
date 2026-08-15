#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check November 24, 2025 backup (4layer_complete)
"""
import json, sys, io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "=" * 80)
print("NOVEMBER 24, 2025 BACKUP ANALYSIS (4layer_complete)")
print("=" * 80)

print("\nLoading backup...")
with open('backups/regulatory_provisions_4layer_complete_20251124_081014.json', 'r') as f:
    data = json.load(f)
    if isinstance(data, dict):
        records = data.get('data', [])
        metadata = {k: v for k, v in data.items() if k != 'data'}
    else:
        records = data
        metadata = {}

print(f"Total records: {len(records):,}")

if metadata:
    print("\nBackup metadata:")
    for k, v in metadata.items():
        if k != 'data':
            print(f"  {k}: {v}")

# Check columns
if records:
    first_record = records[0]
    columns = list(first_record.keys())
    v2_columns = [c for c in columns if c.startswith('v2_')]

    print(f"\nTotal columns: {len(columns)}")
    print(f"v2_ columns: {len(v2_columns)}")

    if v2_columns:
        print("  ✅ This is a POST-v2 backup (v2 enrichment complete)")
        print(f"  v2 columns: {', '.join(sorted(v2_columns)[:5])}...")
    else:
        print("  ❌ This is a PRE-v2 backup (no v2 enrichment)")

    # Check Leichhardt
    leichhardt = [r for r in records if 'Leichhardt' in r.get('document_id', '')]
    print(f"\nLeichhardt provisions: {len(leichhardt):,}")

    if not leichhardt:
        print("  ❌ NO LEICHHARDT PROVISIONS FOUND")
        print("  This backup may be incomplete or a test export")
        sys.exit(1)

    null_pages = sum(1 for r in leichhardt if r.get('pdf_page') is None)
    has_pages = sum(1 for r in leichhardt if r.get('pdf_page') is not None)

    print(f"\npdf_page status:")
    print(f"  NULL: {null_pages:,} ({null_pages/len(leichhardt)*100:.1f}%)")
    print(f"  Has value: {has_pages:,} ({has_pages/len(leichhardt)*100:.1f}%)")

    # Check generic layer if v2 columns exist
    if 'v2_dcp_layer' in columns:
        generic = [r for r in leichhardt if r.get('v2_dcp_layer') == 'generic']
        print(f"\nGeneric layer: {len(generic):,}")

        if generic:
            generic_null = sum(1 for r in generic if r.get('pdf_page') is None)
            generic_has = sum(1 for r in generic if r.get('pdf_page') is not None)
            print(f"  NULL pdf_page: {generic_null:,} ({generic_null/len(generic)*100:.1f}%)")
            print(f"  Has pdf_page: {generic_has:,} ({generic_has/len(generic)*100:.1f}%)")

            # Check Part C Section 1
            part_c1 = [r for r in generic if r.get('v2_dcp_part') and 'Part C Section 1' in r.get('v2_dcp_part', '')]
            if part_c1:
                print(f"\nPart C Section 1 (generic): {len(part_c1):,}")
                c1_null = sum(1 for r in part_c1 if r.get('pdf_page') is None)
                c1_has = sum(1 for r in part_c1 if r.get('pdf_page') is not None)
                print(f"  NULL pdf_page: {c1_null:,} ({c1_null/len(part_c1)*100:.1f}%)")
                print(f"  Has pdf_page: {c1_has:,} ({c1_has/len(part_c1)*100:.1f}%)")

print("\n" + "=" * 80)
print("COMPARISON WITH OTHER BACKUPS")
print("=" * 80)

print(f"\n{'Backup':<25} {'Total':<10} {'Leichhardt':<12} {'NULL pdf_page':<15} {'Has v2?':<8}")
print("-" * 80)
print(f"{'Nov 22 (pre-v2)':<25} {'48,374':<10} {'3,355':<12} {'67.3%':<15} {'No':<8}")
print(f"{'Nov 24 (4layer)':<25} {len(records):<10} {len(leichhardt):<12} {f'{null_pages/len(leichhardt)*100:.1f}%':<15} {'Yes' if v2_columns else 'No':<8}")
print(f"{'Current DB':<25} {'48,374':<10} {'2,990':<12} {'~67%':<15} {'Yes':<8}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

if len(records) < 10000:
    print("\n❌ CANNOT USE THIS BACKUP")
    print(f"   Only {len(records):,} provisions (incomplete)")
    print("   This appears to be a test export or partial backup")
    print("\n   Next steps:")
    print("   1. Look for other backups between Nov 22 and Jan 27")
    print("   2. Check extraction logs for pdf_page population")
    print("   3. Consider reconstructing pdf_page from source documents")

elif null_pages / len(leichhardt) > 0.5:
    print("\n❌ THIS BACKUP ALSO HAS NULL pdf_page ISSUE")
    print(f"   {null_pages/len(leichhardt)*100:.1f}% of Leichhardt provisions have NULL pdf_page")
    print("\n   The problem existed in November 2025")
    print("\n   Next steps:")
    print("   1. Check for backups after November 24")
    print("   2. Look for pdf_page population scripts in git history")
    print("   3. Consider reconstructing from extraction metadata")

else:
    print("\n✅ THIS BACKUP HAS BETTER pdf_page DATA!")
    print(f"   Only {null_pages/len(leichhardt)*100:.1f}% NULL (vs 67% in Nov 22)")
    print(f"   Has v2 columns: {'Yes' if v2_columns else 'No'}")
    print("\n   RECOMMENDED ACTION:")
    print("   1. Backup current database:")
    print("      python scripts/create_full_backup.py")
    print("   2. Restore from November 24 backup:")
    print("      python scripts/restore_from_backup.py backups/regulatory_provisions_4layer_complete_20251124_081014.json")
    if not v2_columns:
        print("   3. Re-run v2 enrichment:")
        print("      python scripts/re_enrich_all.py")
    print("   4. Test API (should return 2,000+ provisions)")
    print("   5. Create fresh backup")

print("\n" + "=" * 80)
