import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

print("DATA QUALITY CHECK - What 21 Controls Actually Contain")
print("="*80)

# Get the actual 15 controls returned by API
cur.execute("""
    SELECT
        dc.control_type,
        dc.control_subtype,
        dc.value_numeric,
        dc.unit,
        dc.confidence_score,
        rp.ref_number,
        LEFT(rp.provision_text, 80) as text
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE rp.zone = 'R2'
      AND dc.control_type IN ('height', 'setback', 'parking', 'fsr', 'open_space')
      AND dc.confidence_score::numeric > 0.75
      AND dc.value_numeric IS NOT NULL
    ORDER BY dc.confidence_score::numeric DESC
    LIMIT 15;
""")

print("\n15 controls from development_controls:")
print(f"{'Type':<12} {'Subtype':<15} {'Value':>8} {'Unit':<8} {'Conf':>5} Ref")
print("-"*80)

results = cur.fetchall()
by_type = {}
issues = []

for i, row in enumerate(results, 1):
    ctype, subtype, value, unit, conf, ref, text = row
    print(f"{ctype:<12} {(subtype or 'N/A'):<15} {value:>8} {(unit or 'N/A'):<8} {conf:>5} {(ref or 'N/A')[:30]}")
    by_type[ctype] = by_type.get(ctype, 0) + 1

    # Check for issues
    val_num = float(value) if value else 0
    if ctype == 'height' and val_num > 100:
        issues.append(f"Row {i}: Height={value}m is likely YEAR not metres (from '{ref}')")
    if ctype == 'setback' and val_num > 50:
        issues.append(f"Row {i}: Setback={value}m seems too large")

print(f"\n\nDistribution:")
for ctype, count in sorted(by_type.items()):
    print(f"  {ctype}: {count} controls")

# Get the 6 curated rules
cur.execute("""
    SELECT boundary_type, base_value, unit, source_document
    FROM zone_setback_rules
    WHERE zone = 'R2'
    ORDER BY boundary_type;
""")

print(f"\n\n6 curated setback rules from zone_setback_rules:")
setback_areas = {}
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} {row[2]} ({row[3][:40]}...)")
    area = "Ashfield" if "Ashfield" in row[3] else "Leichhardt"
    setback_areas[area] = setback_areas.get(area, 0) + 1

print(f"\n  Areas covered: {', '.join(setback_areas.keys())}")

cur.close()
conn.close()

print("\n" + "="*80)
print("QUALITY ISSUES:")
if issues:
    for issue in issues:
        print(f"  ! {issue}")
else:
    print("  No obvious errors detected in values")

print("\nSTRUCTURAL ISSUES:")
print("  1. Multiple height controls (", by_type.get('height', 0), ") - should deduplicate")
print("  2. Both Ashfield AND Leichhardt setbacks shown")
print("     -> Should determine property's actual DCP area")
print("  3. No property-specific filtering (shows all R2 controls)")
print("  4. Values like 2011m, 2022m suggest year extraction errors")

print("\n" + "="*80)
print("PROFESSIONAL STANDARD:")
print("  Current: 21 controls (15 extracted + 6 curated)")
print("  Expected: 7-10 RELEVANT controls per property:")
print("    - 1 height limit (most restrictive)")
print("    - 1 FSR limit")
print("    - 1 front setback (for actual DCP area)")
print("    - 1 side setback")
print("    - 1 rear setback")
print("    - 2-4 other requirements (parking, landscaping)")
print("\n  STATUS: Needs filtering/deduplication for professional quality")