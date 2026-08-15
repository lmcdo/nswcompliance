#!/usr/bin/env python3
"""Check why TOC/intro/history is in actionable provisions"""
import os
import sys
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("=" * 60)
print("TOC/INTRO/HISTORY IN ACTIONABLE PROVISIONS")
print("=" * 60)

# 1. TOC patterns
print("\n1. TABLE OF CONTENTS patterns (v2_is_actionable=true):")
cur.execute('''
    SELECT COUNT(*),
           CASE WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
                WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
                WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
                ELSE 'Other' END
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (
        provision_text LIKE '%...%...%' OR
        provision_text LIKE '%.....%' OR
        provision_text ~ '\\.\\.\\s*[0-9]+$' OR
        provision_text ILIKE '%table of contents%' OR
        provision_text ILIKE '%contents page%'
    )
    GROUP BY 2
''')
for row in cur.fetchall():
    print(f"   {row[1]}: {row[0]}")

print("\n   Samples:")
cur.execute('''
    SELECT LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (provision_text LIKE '%...%...%' OR provision_text LIKE '%.....%')
    LIMIT 5
''')
for row in cur.fetchall():
    print(f"   - {row[0]}...")

# 2. Introduction patterns
print("\n2. INTRODUCTION patterns (v2_is_actionable=true):")
cur.execute('''
    SELECT COUNT(*),
           CASE WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
                WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
                WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
                ELSE 'Other' END
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (
        provision_text ILIKE 'this development control plan%' OR
        provision_text ILIKE 'this plan applies%' OR
        provision_text ILIKE 'the purpose of this%' OR
        provision_text ILIKE 'this dcp%' OR
        provision_text ILIKE '%name of this plan%' OR
        provision_text ILIKE '%when this plan came into force%'
    )
    GROUP BY 2
''')
for row in cur.fetchall():
    print(f"   {row[1]}: {row[0]}")

print("\n   Samples:")
cur.execute('''
    SELECT LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (provision_text ILIKE 'this development control plan%' OR provision_text ILIKE 'this plan applies%')
    LIMIT 5
''')
for row in cur.fetchall():
    print(f"   - {row[0]}...")

# 3. History patterns
print("\n3. HISTORY/DESCRIPTIVE patterns (v2_is_actionable=true):")
cur.execute('''
    SELECT COUNT(*),
           CASE WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
                WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
                WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
                ELSE 'Other' END
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (
        provision_text ~ 'in the (18|19)[0-9]{2}' OR
        provision_text ILIKE '%was built in%' OR
        provision_text ILIKE '%were constructed%' OR
        provision_text ILIKE '%has evolved%' OR
        provision_text ILIKE '%dates from%' OR
        provision_text ILIKE '%historically%'
    )
    GROUP BY 2
''')
for row in cur.fetchall():
    print(f"   {row[1]}: {row[0]}")

print("\n   Samples:")
cur.execute('''
    SELECT LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (provision_text ~ 'in the (18|19)[0-9]{2}' OR provision_text ILIKE '%was built in%')
    LIMIT 5
''')
for row in cur.fetchall():
    print(f"   - {row[0]}...")

# 4. Check what v2_provision_type these have
print("\n4. v2_provision_type of TOC/intro/history:")
cur.execute('''
    SELECT v2_provision_type, COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (
        provision_text LIKE '%...%...%' OR
        provision_text ILIKE 'this development control plan%' OR
        provision_text ~ 'in the (18|19)[0-9]{2}'
    )
    GROUP BY v2_provision_type
    ORDER BY 2 DESC
''')
for row in cur.fetchall():
    print(f"   {row[0] or 'NULL'}: {row[1]}")

# 5. Total counts
print("\n5. TOTAL CONTAMINATION:")
cur.execute('''
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (
        provision_text LIKE '%...%...%' OR
        provision_text LIKE '%.....%' OR
        provision_text ILIKE 'this development control plan%' OR
        provision_text ILIKE 'this plan applies%' OR
        provision_text ILIKE '%name of this plan%' OR
        provision_text ~ 'in the (18|19)[0-9]{2}' OR
        provision_text ILIKE '%was built in%' OR
        provision_text ILIKE '%has evolved%'
    )
''')
total = cur.fetchone()[0]
print(f"   Provisions that should NOT be actionable: {total}")

cur.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true')
all_actionable = cur.fetchone()[0]
print(f"   Total actionable: {all_actionable}")
print(f"   Contamination rate: {round(100*total/all_actionable, 1)}%")

conn.close()
