#!/usr/bin/env python3
"""
Comprehensive audit of the classifier pipeline for flaws.
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
print("CLASSIFIER PIPELINE AUDIT")
print("=" * 70)

# =============================================================================
# FLAW 1: Document type detection (underscore bug)
# =============================================================================
print("\n" + "=" * 70)
print("FLAW 1: Document Type Detection")
print("=" * 70)

# How many LEP documents exist?
cur.execute("""
    SELECT COUNT(DISTINCT document_id) FROM regulatory_provisions
    WHERE document_id ILIKE '%Local_Environmental_Plan%'
       OR document_id ILIKE '%LEP%'
""")
lep_docs = cur.fetchone()[0]

# How many SEPP documents exist?
cur.execute("""
    SELECT COUNT(DISTINCT document_id) FROM regulatory_provisions
    WHERE document_id ILIKE '%State_Environmental_Planning_Policy%'
       OR document_id ILIKE '%SEPP%'
""")
sepp_docs = cur.fetchone()[0]

# How many LEP/SEPP provisions are marked NOT actionable?
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (document_id ILIKE '%Local_Environmental_Plan%'
         OR document_id ILIKE '%State_Environmental_Planning_Policy%')
""")
lep_sepp_excluded = cur.fetchone()[0]

# How many of those have control language?
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (document_id ILIKE '%Local_Environmental_Plan%'
         OR document_id ILIKE '%State_Environmental_Planning_Policy%')
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
""")
lep_sepp_excluded_with_control = cur.fetchone()[0]

print(f"LEP documents in database: {lep_docs}")
print(f"SEPP documents in database: {sepp_docs}")
print(f"LEP/SEPP provisions excluded: {lep_sepp_excluded}")
print(f"LEP/SEPP excluded WITH control language (must/shall): {lep_sepp_excluded_with_control}")
print(f"  -> These are likely FALSE NEGATIVES from underscore bug")

# =============================================================================
# FLAW 2: Short text rejection (<10 chars)
# =============================================================================
print("\n" + "=" * 70)
print("FLAW 2: Short Text Rejection (<10 chars)")
print("=" * 70)

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE LENGTH(provision_text) < 10
""")
very_short = cur.fetchone()[0]

cur.execute("""
    SELECT id, provision_text FROM regulatory_provisions
    WHERE LENGTH(provision_text) < 10
    AND LENGTH(provision_text) > 0
    LIMIT 10
""")
short_examples = cur.fetchall()

print(f"Provisions under 10 chars: {very_short}")
if short_examples:
    print("Examples:")
    for id, text in short_examples:
        print(f"  [{id}] '{text}'")

# =============================================================================
# FLAW 3: Overly broad boilerplate patterns
# =============================================================================
print("\n" + "=" * 70)
print("FLAW 3: Boilerplate Pattern Analysis")
print("=" * 70)

# Check if any boilerplate patterns match legitimate controls
patterns_to_check = [
    ("Interpretation Act", "%Interpretation Act%"),
    ("section 45C", "%section 45C%"),
    ("published on the NSW", "%published on the NSW%"),
]

for name, pattern in patterns_to_check:
    # Find excluded provisions matching this pattern that also have control language
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND provision_text ILIKE '{pattern}'
        AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%'
             OR provision_text ILIKE '%minimum%' OR provision_text ILIKE '%maximum%')
    """)
    count = cur.fetchone()[0]
    if count > 0:
        print(f"Pattern '{name}': {count} excluded provisions also have control language")
        # Show example
        cur.execute(f"""
            SELECT id, LEFT(provision_text, 200) FROM regulatory_provisions
            WHERE v2_is_actionable = false
            AND provision_text ILIKE '{pattern}'
            AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
            LIMIT 2
        """)
        for id, text in cur.fetchall():
            print(f"    [{id}] {text}...")

# =============================================================================
# FLAW 4: DCP documents marked as non-actionable
# =============================================================================
print("\n" + "=" * 70)
print("FLAW 4: DCP Documents Incorrectly Excluded")
print("=" * 70)

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND document_id ILIKE '%DCP%'
""")
dcp_excluded = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND document_id ILIKE '%DCP%'
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%'
         OR provision_text ILIKE '%minimum%' OR provision_text ILIKE '%setback%')
""")
dcp_excluded_with_control = cur.fetchone()[0]

print(f"DCP provisions excluded: {dcp_excluded}")
print(f"DCP excluded WITH control language: {dcp_excluded_with_control}")

if dcp_excluded_with_control > 0:
    cur.execute("""
        SELECT id, document_id, LEFT(provision_text, 200) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND document_id ILIKE '%DCP%'
        AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
        LIMIT 5
    """)
    print("Examples of potentially wrongly excluded DCP provisions:")
    for id, doc, text in cur.fetchall():
        print(f"  [{id}] {doc[:50]}")
        print(f"       {text[:150]}...")

# =============================================================================
# FLAW 5: Check actionable pattern coverage
# =============================================================================
print("\n" + "=" * 70)
print("FLAW 5: Actionable Pattern Coverage Gaps")
print("=" * 70)

# What control words are in excluded provisions?
control_words = ['must', 'shall', 'required', 'minimum', 'maximum', 'prohibited', 'permitted']
print("Excluded provisions containing control words:")
for word in control_words:
    cur.execute(f"""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND provision_text ILIKE '%{word}%'
    """)
    count = cur.fetchone()[0]
    print(f"  '{word}': {count}")

# =============================================================================
# FLAW 6: Numbered controls (C1, C2) that were excluded
# =============================================================================
print("\n" + "=" * 70)
print("FLAW 6: Numbered Controls (C1, C2, etc.) Excluded")
print("=" * 70)

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND provision_text ~ '^C[0-9]+'
""")
c_excluded = cur.fetchone()[0]

print(f"Provisions starting with C[number] but excluded: {c_excluded}")

if c_excluded > 0:
    cur.execute("""
        SELECT id, LEFT(provision_text, 150) FROM regulatory_provisions
        WHERE v2_is_actionable = false
        AND provision_text ~ '^C[0-9]+'
        LIMIT 5
    """)
    print("Examples:")
    for id, text in cur.fetchall():
        print(f"  [{id}] {text}...")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY OF POTENTIAL FALSE NEGATIVES")
print("=" * 70)

cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false")
total_excluded = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true")
total_included = cur.fetchone()[0]

print(f"Total provisions: {total_excluded + total_included}")
print(f"Currently included: {total_included}")
print(f"Currently excluded: {total_excluded}")
print(f"")
print(f"Potential false negatives identified:")
print(f"  - LEP/SEPP with control language (underscore bug): {lep_sepp_excluded_with_control}")
print(f"  - DCP with control language: {dcp_excluded_with_control}")
print(f"  - Numbered controls (C1, C2) excluded: {c_excluded}")
print(f"")
estimated_fn = lep_sepp_excluded_with_control + dcp_excluded_with_control + c_excluded
print(f"Estimated total false negatives: ~{estimated_fn}")
print(f"As percentage of excluded: {estimated_fn/total_excluded*100:.2f}%")
print(f"As percentage of total: {estimated_fn/(total_excluded+total_included)*100:.2f}%")

conn.close()
