#!/usr/bin/env python3
"""Count provisions excluded due to blank line bug."""
import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# The buggy pattern
buggy_pattern = re.compile(r'^[\s\.\-_]+$', re.IGNORECASE | re.MULTILINE)

# The fixed pattern (only matches if ENTIRE string is whitespace)
fixed_pattern = re.compile(r'\A[\s\.\-_]+\Z', re.IGNORECASE)

# Get all excluded provisions
cur.execute("""
    SELECT id, provision_text FROM regulatory_provisions
    WHERE v2_is_actionable = false
""")

total_excluded = 0
buggy_matches = 0
fixed_matches = 0
false_negatives_from_bug = 0

# Also count those with control language
control_pattern = re.compile(r'\b(must|shall|minimum|maximum|setback|height)\b', re.IGNORECASE)

print("Analyzing excluded provisions...")

rows = cur.fetchall()
total_excluded = len(rows)

for id, text in rows:
    if not text:
        continue

    buggy_match = buggy_pattern.search(text)
    fixed_match = fixed_pattern.search(text)

    if buggy_match:
        buggy_matches += 1

        # Would this be fixed by the corrected pattern?
        if not fixed_match:
            false_negatives_from_bug += 1

            # Does it have control language?
            if control_pattern.search(text):
                # This is a real control excluded by the bug
                pass

print()
print("=" * 60)
print("BLANK LINE BUG IMPACT ANALYSIS")
print("=" * 60)
print()
print(f"Total excluded provisions: {total_excluded}")
print(f"Matched by buggy pattern ^[\\s\\.\\-_]+$: {buggy_matches}")
print(f"Would match fixed pattern \\A[\\s\\.\\-_]+\\Z: {fixed_matches}")
print(f"FALSE NEGATIVES from this bug alone: {false_negatives_from_bug}")
print()
print(f"This bug accounts for {false_negatives_from_bug/total_excluded*100:.1f}% of exclusions")

# Now check how many of those false negatives have control language
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text LIKE '%' || chr(10) || chr(10) || '%'
         OR provision_text LIKE chr(10) || '%')
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
""")
controls_with_leading_newline = cur.fetchone()[0]

print(f"Excluded provisions with leading newlines AND control language: {controls_with_leading_newline}")

conn.close()
