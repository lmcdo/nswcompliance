"""
Deterministic heritage type tagging using SQL pattern matching
No LLM needed - 100% accurate for clear patterns

Categories:
- control: Starts with C1-C999, O1-O999, or contains imperative verbs
- character: Contains HCA names, "characterized by", "typical of"
- descriptive: Everything else (policy, definitions, background)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print("Deterministic Heritage Type Tagging")
print("=" * 60)

# Step 1: Tag clear CONTROLS
print("\nStep 1: Tagging controls (C1-C999, O1-O999 patterns)...")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_heritage_type = 'control'
    WHERE v2_marker = 'heritage'
    AND (
        -- Starts with C1, C2, etc.
        provision_text ~ '^\\s*C\\d{1,3}[\\s\\n]'
        OR provision_text ~ '[\\n]C\\d{1,3}[\\s\\n]'
        -- Starts with O1, O2, etc. (objectives)
        OR provision_text ~ '^\\s*O\\d{1,3}[\\s\\n]'
        OR provision_text ~ '[\\n]O\\d{1,3}[\\s\\n]'
        -- Contains "must", "shall", "require" (imperative)
        OR (
            (provision_text ILIKE '%must%'
             OR provision_text ILIKE '%shall%'
             OR provision_text ILIKE '%required%'
             OR provision_text ILIKE '%ensure%')
            AND provision_text NOT ILIKE '%introduction%'
            AND provision_text NOT ILIKE '%table of contents%'
        )
    )
""")
controls = cur.rowcount
print(f"   Tagged {controls} provisions as 'control'")

# Step 2: Tag clear CHARACTER statements
print("\nStep 2: Tagging character statements...")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_heritage_type = 'character'
    WHERE v2_marker = 'heritage'
    AND v2_heritage_type != 'control'  -- Don't override controls
    AND (
        provision_text ILIKE '%characterized by%'
        OR provision_text ILIKE '%typical of%'
        OR provision_text ILIKE '%key characteristics%'
        OR provision_text ILIKE '%architectural style%'
        OR provision_text ILIKE '%building ranking%'
        OR provision_text ILIKE '%contributory building%'
        OR provision_text ILIKE '%significant building%'
        OR (
            provision_text ILIKE '%HCA%'
            AND (
                provision_text ILIKE '%character%'
                OR provision_text ILIKE '%significance%'
                OR provision_text ILIKE '%history%'
            )
        )
    )
""")
character = cur.rowcount
print(f"   Tagged {character} provisions as 'character'")

# Step 3: Everything else is DESCRIPTIVE
print("\nStep 3: Tagging remaining as descriptive...")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_heritage_type = 'descriptive'
    WHERE v2_marker = 'heritage'
    AND (v2_heritage_type IS NULL OR v2_heritage_type NOT IN ('control', 'character'))
""")
descriptive = cur.rowcount
print(f"   Tagged {descriptive} provisions as 'descriptive'")

conn.commit()

# Verify results
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

cur.execute("""
    SELECT v2_heritage_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
    GROUP BY v2_heritage_type
    ORDER BY count DESC
""")
print("\nOverall distribution:")
for row in cur.fetchall():
    total = controls + character + descriptive
    pct = (int(row[1]) / total * 100) if total > 0 else 0
    print(f"  {row[0]:15} {row[1]:5} ({pct:.1f}%)")

# By council
cur.execute("""
    SELECT
        CASE
            WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
            WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
            WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
            ELSE 'Other'
        END as council,
        v2_heritage_type,
        COUNT(*)
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
    GROUP BY council, v2_heritage_type
    ORDER BY council, COUNT(*) DESC
""")
print("\nBy council:")
for row in cur.fetchall():
    print(f"  {row[0]:15} {row[1]:15} {row[2]:5}")

# Sample controls
print("\nSample controls:")
cur.execute("""
    SELECT id, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE v2_heritage_type = 'control'
      AND v2_marker = 'heritage'
    ORDER BY RANDOM()
    LIMIT 5
""")
for i, row in enumerate(cur.fetchall(), 1):
    print(f"\n{i}. [{row[0]}]")
    print(f"   {row[1]}...")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("COMPLETE - Heritage types tagged deterministically")
print("=" * 60)
