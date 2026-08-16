#!/usr/bin/env python3
"""
Comprehensive audit for ALL potential false negative sources.
"""
import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 70)
print("COMPREHENSIVE FALSE NEGATIVE AUDIT")
print("=" * 70)

# =============================================================================
# 1. CONTROL LANGUAGE IN EXCLUDED PROVISIONS
# =============================================================================
print("\n" + "=" * 70)
print("1. CONTROL LANGUAGE ANALYSIS")
print("=" * 70)

control_words = [
    ('must', '%must%'),
    ('shall', '%shall%'),
    ('required', '%required%'),
    ('is to', '%is to%'),
    ('are to', '%are to%'),
    ('minimum', '%minimum%'),
    ('maximum', '%maximum%'),
    ('at least', '%at least%'),
    ('no more than', '%no more than%'),
    ('not exceed', '%not exceed%'),
    ('prohibited', '%prohibited%'),
    ('not permitted', '%not permitted%'),
    ('setback', '%setback%'),
    ('height limit', '%height%limit%'),
    ('floor space ratio', '%floor space ratio%'),
    ('FSR', '%FSR%'),
]

print("\nExcluded provisions containing control language:")
for name, pattern in control_words:
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND provision_text ILIKE '{pattern}'
    """)
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  '{name}': {count}")

# =============================================================================
# 2. NUMBERED MARKERS IN EXCLUDED PROVISIONS
# =============================================================================
print("\n" + "=" * 70)
print("2. NUMBERED MARKERS IN EXCLUDED PROVISIONS")
print("=" * 70)

markers = [
    ('^C[0-9]+', 'Control markers (C1, C2...)'),
    ('^O[0-9]+', 'Objective markers (O1, O2...)'),
    ('^P[0-9]+', 'Performance markers (P1, P2...)'),
    ('^[0-9]+\\.', 'Section numbers (1., 2.1...)'),
    ('\\([a-z]\\)', 'Lettered clauses (a), (b)...'),
]

for pattern, desc in markers:
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND provision_text ~ '{pattern}'
    """)
    count = cur.fetchone()[0]
    print(f"  {desc}: {count}")

# =============================================================================
# 3. NUMERIC VALUES IN EXCLUDED PROVISIONS
# =============================================================================
print("\n" + "=" * 70)
print("3. NUMERIC VALUES IN EXCLUDED PROVISIONS")
print("=" * 70)

numeric_patterns = [
    ('[0-9]+\\s*m\\b', 'Metres (6m, 6 m)'),
    ('[0-9]+\\s*metres', 'Metres spelled out'),
    ('[0-9]+\\s*storeys', 'Storeys'),
    ('[0-9]+\\s*%', 'Percentages'),
    ('[0-9]+:[0-9]+', 'Ratios (0.5:1)'),
    ('[0-9]+\\s*m2', 'Square metres'),
]

for pattern, desc in numeric_patterns:
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND provision_text ~* '{pattern}'
    """)
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  {desc}: {count}")

# =============================================================================
# 4. EACH BOILERPLATE PATTERN'S COLLATERAL DAMAGE
# =============================================================================
print("\n" + "=" * 70)
print("4. BOILERPLATE PATTERN COLLATERAL DAMAGE")
print("=" * 70)

boilerplate_patterns = [
    ('Parliamentary Counsel', '%Parliamentary Counsel%'),
    ('compiled and maintained', '%compiled and maintained%'),
    ('NSW legislation website', '%NSW legislation website%'),
    ('Interpretation Act', '%Interpretation Act%'),
    ('section 45C', '%section 45C%'),
    ('certified as the form', '%certified as the form%'),
    ('Historical versions', '%Historical versions%'),
    ('currency of this information', '%currency of this information%'),
    ('This Policy is State', '%This Policy is State%'),
    ('This Plan is % LEP', '%This Plan is%Local Environmental Plan%'),
    ('Environmental Planning and Assessment Act', '%Environmental Planning and Assessment Act%'),
    ('published on the NSW', '%published on the NSW%'),
    ('published in % Gazette', '%published in%Gazette%'),
    ('Figure + number', 'Figure [0-9]'),
    ('Map + number', 'Map [0-9]'),
    ('Source:', '%Source:%'),
]

print("\nExcluded provisions matching boilerplate patterns that ALSO have control words:")
for name, pattern in boilerplate_patterns:
    if pattern.startswith('%'):
        cur.execute(f"""
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = false
            AND provision_text ILIKE '{pattern}'
            AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%'
                 OR provision_text ILIKE '%minimum%' OR provision_text ILIKE '%maximum%')
        """)
    else:
        cur.execute(f"""
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = false
            AND provision_text ~* '{pattern}'
            AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%'
                 OR provision_text ILIKE '%minimum%' OR provision_text ILIKE '%maximum%')
        """)
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  '{name}': {count} also have control language")

# =============================================================================
# 5. SHORT TEXT ANALYSIS
# =============================================================================
print("\n" + "=" * 70)
print("5. SHORT TEXT EXCLUSIONS")
print("=" * 70)

length_buckets = [
    (0, 10, 'Under 10 chars'),
    (10, 50, '10-50 chars'),
    (50, 100, '50-100 chars'),
    (100, 150, '100-150 chars'),
]

for min_len, max_len, desc in length_buckets:
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND LENGTH(provision_text) >= {min_len}
        AND LENGTH(provision_text) < {max_len}
    """)
    total = cur.fetchone()[0]

    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND LENGTH(provision_text) >= {min_len}
        AND LENGTH(provision_text) < {max_len}
        AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
    """)
    with_control = cur.fetchone()[0]

    print(f"  {desc}: {total} excluded ({with_control} have control language)")

# =============================================================================
# 6. DOCUMENT TYPE MISCLASSIFICATION
# =============================================================================
print("\n" + "=" * 70)
print("6. DOCUMENT TYPE PATTERNS NOT MATCHING")
print("=" * 70)

# Documents with "DCP" that might not match pattern
cur.execute("""
    SELECT DISTINCT document_id FROM regulatory_provisions
    WHERE document_id ILIKE '%development%control%plan%'
    AND document_id NOT ILIKE '%DCP%'
    LIMIT 10
""")
dcp_variants = cur.fetchall()
print(f"\nDocs with 'Development Control Plan' but no 'DCP': {len(dcp_variants)}")
for row in dcp_variants[:5]:
    print(f"  {row[0][:70]}")

# Documents with LEP variants
cur.execute("""
    SELECT DISTINCT document_id FROM regulatory_provisions
    WHERE (document_id ILIKE '%local%environmental%plan%'
           OR document_id ILIKE '%LEP%')
    LIMIT 10
""")
lep_docs = cur.fetchall()
print(f"\nLEP document name samples:")
for row in lep_docs[:5]:
    print(f"  {row[0][:70]}")

# =============================================================================
# 7. SPECIAL CHARACTERS / ENCODING ISSUES
# =============================================================================
print("\n" + "=" * 70)
print("7. SPECIAL CHARACTERS IN EXCLUDED PROVISIONS")
print("=" * 70)

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text LIKE '%' || chr(160) || '%'
         OR provision_text LIKE '%' || chr(8211) || '%'
         OR provision_text LIKE '%' || chr(8212) || '%'
         OR provision_text LIKE '%' || chr(8217) || '%')
""")
special_char_count = cur.fetchone()[0]
print(f"Excluded provisions with special chars (non-breaking space, em-dash, etc.): {special_char_count}")

# =============================================================================
# 8. MULTI-LINE TEXT WITH CONTROLS BURIED INSIDE
# =============================================================================
print("\n" + "=" * 70)
print("8. LONG EXCLUDED PROVISIONS WITH CONTROLS")
print("=" * 70)

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND LENGTH(provision_text) > 200
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
""")
long_with_control = cur.fetchone()[0]
print(f"Excluded provisions >200 chars with control language: {long_with_control}")

# Sample
cur.execute("""
    SELECT id, LEFT(provision_text, 300) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND LENGTH(provision_text) > 200
    AND provision_text ILIKE '%must%'
    LIMIT 3
""")
samples = cur.fetchall()
print("\nSamples:")
for id, text in samples:
    print(f"\n  [{id}] {text}...")

# =============================================================================
# 9. CHECK WHAT'S IN ACTIONABLE=TRUE FOR COMPARISON
# =============================================================================
print("\n" + "=" * 70)
print("9. COMPARISON: WHAT GOT INCLUDED")
print("=" * 70)

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true
""")
included = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
""")
included_with_control = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND provision_text !~* '(must|shall|minimum|maximum|required|prohibited)'
""")
included_without_control = cur.fetchone()[0]

print(f"Total included: {included}")
print(f"Included WITH control language: {included_with_control}")
print(f"Included WITHOUT any control language: {included_without_control}")

# =============================================================================
# 10. COMBINED FALSE NEGATIVE ESTIMATE
# =============================================================================
print("\n" + "=" * 70)
print("10. COMBINED FALSE NEGATIVE ESTIMATE")
print("=" * 70)

# Most conservative: excluded provisions with strong control signals
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (
        -- Has mandatory language
        (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
        -- AND has specific control content
        AND (provision_text ILIKE '%setback%'
             OR provision_text ILIKE '%height%'
             OR provision_text ILIKE '%minimum%'
             OR provision_text ILIKE '%maximum%'
             OR provision_text ~* '^C[0-9]+'
             OR provision_text ~* '[0-9]+\\s*m\\b')
    )
""")
strong_false_neg = cur.fetchone()[0]

# Moderate: just has mandatory language
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
""")
moderate_false_neg = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
""")
total = cur.fetchone()[0]

print(f"\nTotal provisions: {total}")
print(f"Currently excluded: {total - included}")
print(f"Currently included: {included}")
print()
print(f"STRONG false negative candidates: {strong_false_neg}")
print(f"  (has must/shall + specific control content)")
print(f"  = {strong_false_neg/total*100:.1f}% of total")
print()
print(f"MODERATE false negative candidates: {moderate_false_neg}")
print(f"  (has must/shall)")
print(f"  = {moderate_false_neg/total*100:.1f}% of total")

conn.close()
