#!/usr/bin/env python3
"""Complete audit of ALL extracted data quality"""

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)
cur = conn.cursor()

print("="*80)
print("COMPLETE DATA QUALITY AUDIT - ALL 4,526 EXTRACTED CONTROLS")
print("="*80)

# Check ALL controls for obvious errors
print("\n[1] Checking for value extraction errors...\n")

cur.execute("""
    SELECT
        control_type,
        COUNT(*) as total,
        COUNT(CASE WHEN value_numeric::numeric > 100 THEN 1 END) as suspiciously_large,
        COUNT(CASE WHEN value_numeric::numeric < 0.01 THEN 1 END) as suspiciously_small,
        MIN(value_numeric::numeric) as min_val,
        MAX(value_numeric::numeric) as max_val,
        AVG(value_numeric::numeric) as avg_val
    FROM development_controls
    WHERE value_numeric IS NOT NULL
    GROUP BY control_type
    ORDER BY total DESC;
""")

print(f"{'Type':<15} {'Total':>7} {'Large(>100)':>12} {'Small(<0.01)':>14} {'Min':>8} {'Max':>10} {'Avg':>8}")
print("-"*80)

issues_by_type = {}
for row in cur.fetchall():
    ctype, total, large, small, min_val, max_val, avg_val = row
    print(f"{ctype:<15} {total:>7} {large:>12} {small:>14} {float(min_val):>8.2f} {float(max_val):>10.1f} {float(avg_val):>8.2f}")

    if large > 0:
        issues_by_type[ctype] = issues_by_type.get(ctype, 0) + large

# Sample the bad ones
print("\n\n[2] Sample of BAD extractions (value > 100):\n")

cur.execute("""
    SELECT
        dc.control_type,
        dc.value_numeric,
        dc.unit,
        rp.ref_number,
        LEFT(rp.provision_text, 100) as text
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE dc.value_numeric::numeric > 100
    LIMIT 15;
""")

for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} {row[2] or ''}")
    print(f"    Ref: {row[3]}")
    print(f"    Text: {row[4]}...")
    print()

# Sample the good ones
print("\n[3] Sample of GOOD extractions (reasonable values):\n")

cur.execute("""
    SELECT
        dc.control_type,
        dc.value_numeric,
        dc.unit,
        rp.ref_number,
        LEFT(rp.provision_text, 100) as text
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE dc.value_numeric::numeric BETWEEN 0.1 AND 50
      AND dc.control_type IN ('height', 'setback', 'fsr')
    ORDER BY RANDOM()
    LIMIT 10;
""")

good_count = 0
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} {row[2] or ''}")
    print(f"    Ref: {row[3]}")
    print(f"    Text: {row[4][:60]}...")
    print()
    good_count += 1

# Check confidence scores
print("\n[4] Confidence score distribution:\n")

cur.execute("""
    SELECT
        confidence_score,
        COUNT(*) as count
    FROM development_controls
    WHERE confidence_score IS NOT NULL
    GROUP BY confidence_score
    ORDER BY confidence_score DESC;
""")

for row in cur.fetchall():
    print(f"  Confidence {row[0]}: {row[1]:>5} controls")

# Check extraction method
print("\n\n[5] Extraction methods used:\n")

cur.execute("""
    SELECT
        extraction_method,
        COUNT(*) as count
    FROM development_controls
    WHERE extraction_method IS NOT NULL
    GROUP BY extraction_method
    ORDER BY count DESC;
""")

for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:>5} controls")

cur.close()
conn.close()

print("\n" + "="*80)
print("VERDICT:")
print("="*80)

total_issues = sum(issues_by_type.values())
print(f"\nControls with suspicious values (>100): {total_issues} out of 4,526")
print(f"Percentage of bad data: {(total_issues/4526)*100:.1f}%")

if good_count > 0:
    print(f"\nGood extractions found: {good_count} sampled")
    print("CONCLUSION: Data is MIXED - has both good and bad extractions")
else:
    print("\nCONCLUSION: Data quality is VERY POOR")

print("\nRECOMMENDATION:")
print("  1. Filter out values > 100 (likely years/errors)")
print("  2. Filter out values > 50m for setbacks (likely mm->m errors)")
print("  3. Keep only controls with reasonable values")
print("  4. Consider re-extraction with better validation")