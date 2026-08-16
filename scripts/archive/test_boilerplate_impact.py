#!/usr/bin/env python3
"""Test boilerplate exclusion impact on provisions."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 60)
print("BOILERPLATE EXCLUSION IMPACT ANALYSIS")
print("=" * 60)

# Test 1: How many provisions contain 'Page \d+' at start?
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_text ~ '^Page [0-9]+'
""")
page_start = cur.fetchone()[0]

# Test 2: How many of those are currently marked NOT actionable?
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_text ~ '^Page [0-9]+'
    AND v2_is_actionable = false
""")
page_excluded = cur.fetchone()[0]

# Test 3: Show examples of excluded "Page X" provisions
cur.execute("""
    SELECT id, LEFT(provision_text, 150) FROM regulatory_provisions
    WHERE provision_text ~ '^Page [0-9]+'
    AND v2_is_actionable = false
    LIMIT 5
""")
page_examples = cur.fetchall()

print(f"\nPattern: ^Page [0-9]+")
print(f"  Total matching: {page_start}")
print(f"  Excluded (not actionable): {page_excluded}")
if page_examples:
    print(f"  Examples:")
    for id, text in page_examples:
        print(f"    [{id}] {text}...")

# Test 4: How many contain 'Interpretation Act'?
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_text ILIKE '%Interpretation Act%'
""")
interp_total = cur.fetchone()[0]

# Test 5: How many of those are NOT actionable?
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_text ILIKE '%Interpretation Act%'
    AND v2_is_actionable = false
""")
interp_excluded = cur.fetchone()[0]

# Test 6: Show examples
cur.execute("""
    SELECT id, LEFT(provision_text, 150) FROM regulatory_provisions
    WHERE provision_text ILIKE '%Interpretation Act%'
    AND v2_is_actionable = false
    LIMIT 5
""")
interp_examples = cur.fetchall()

print(f"\nPattern: Interpretation Act")
print(f"  Total matching: {interp_total}")
print(f"  Excluded (not actionable): {interp_excluded}")
if interp_examples:
    print(f"  Examples:")
    for id, text in interp_examples:
        print(f"    [{id}] {text}...")

# Test 7: FALSE NEGATIVE CANDIDATES - excluded but have control language
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
    AND (provision_text ILIKE '%setback%' OR provision_text ILIKE '%height%'
         OR provision_text ILIKE '%minimum%' OR provision_text ILIKE '%maximum%')
""")
false_neg_candidates = cur.fetchone()[0]

# Show examples of potential false negatives
cur.execute("""
    SELECT id, LEFT(provision_text, 200) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
    AND (provision_text ILIKE '%setback%' OR provision_text ILIKE '%height%'
         OR provision_text ILIKE '%minimum%' OR provision_text ILIKE '%maximum%')
    LIMIT 10
""")
fn_examples = cur.fetchall()

print(f"\n" + "=" * 60)
print("FALSE NEGATIVE CANDIDATES")
print("=" * 60)
print(f"Excluded provisions with control language:")
print(f"  (must/shall) + (setback/height/minimum/maximum)")
print(f"  Count: {false_neg_candidates}")
if fn_examples:
    print(f"\n  Examples (potential missed controls):")
    for id, text in fn_examples:
        print(f"\n    [{id}]")
        print(f"    {text}...")

# Test 8: Check each boilerplate pattern's impact
print(f"\n" + "=" * 60)
print("PER-PATTERN EXCLUSION COUNTS")
print("=" * 60)

patterns = [
    ('Parliamentary Counsel', '%Parliamentary Counsel%'),
    ('compiled and maintained', '%compiled and maintained%'),
    ('NSW legislation website', '%NSW legislation website%'),
    ('Interpretation Act', '%Interpretation Act%'),
    ('section 45C', '%section 45C%'),
    ('certified as the form', '%certified as the form%'),
    ('Historical versions', '%Historical versions%'),
    ('currency of this information', '%currency of this information%'),
    ('This Policy is State Environmental', '%This Policy is State Environmental%'),
    ('This Plan is % Local Environmental Plan', '%This Plan is%Local Environmental Plan%'),
    ('made under the Environmental Planning', '%made under the Environmental Planning%'),
    ('published on the NSW legislation', '%published on the NSW legislation%'),
    ('published in % Gazette', '%published in%Gazette%'),
]

for name, pattern in patterns:
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE provision_text ILIKE '{pattern}'
        AND v2_is_actionable = false
    """)
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  {name}: {count} excluded")

# Total excluded
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false
""")
total_excluded = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true
""")
total_included = cur.fetchone()[0]

print(f"\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total provisions: {total_excluded + total_included}")
print(f"Included (actionable): {total_included}")
print(f"Excluded (not actionable): {total_excluded}")
print(f"False negative candidates: {false_neg_candidates} ({false_neg_candidates/total_excluded*100:.2f}% of excluded)")

conn.close()
