#!/usr/bin/env python3
"""
Find where LEP provisions are referenced in the app.
Determines if LEP extraction is needed and why.
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 70)
print("LEP REFERENCE ANALYSIS - Where is LEP needed?")
print("=" * 70)

# 1. Cross-references pointing to LEP
print("\n=== 1. CROSS-REFERENCES TO LEP ===")
cur.execute("""
    SELECT reference_text, reference_type, resolution_status, COUNT(*) as refs
    FROM cross_reference_index
    WHERE reference_text ILIKE '%lep%'
       OR reference_text ILIKE '%local environmental%'
       OR reference_text ILIKE '%inner west%'
    GROUP BY reference_text, reference_type, resolution_status
    ORDER BY refs DESC
    LIMIT 20
""")
lep_crossrefs = cur.fetchall()
if lep_crossrefs:
    print(f"Found {sum(r[3] for r in lep_crossrefs)} cross-references to LEP:")
    for row in lep_crossrefs:
        status = "resolved" if row[2] == 'resolved' else "UNRESOLVED"
        print(f"  {row[3]:3}x [{status:10}]: {row[0][:60]}")
else:
    print("No cross-references explicitly mention LEP")

# 2. DCP provisions that reference LEP clauses (in provision text)
print("\n=== 2. DCP PROVISIONS MENTIONING LEP CLAUSES ===")
cur.execute("""
    SELECT
        document_id,
        COUNT(*) as mentions
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%leichhardt%'
           OR document_id ILIKE '%ashfield%'
           OR document_id ILIKE '%marrickville%')
      AND (provision_text ILIKE '%clause 4.%'
           OR provision_text ILIKE '%clause 5.%'
           OR provision_text ILIKE '%clause 6.%'
           OR provision_text ILIKE '%lep%'
           OR provision_text ILIKE '%local environmental plan%')
    GROUP BY document_id
    ORDER BY mentions DESC
""")
dcp_lep_mentions = cur.fetchall()
total_mentions = sum(r[1] for r in dcp_lep_mentions)
print(f"Found {total_mentions} DCP provisions mentioning LEP clauses:")
for row in dcp_lep_mentions:
    print(f"  {row[0][:50]}: {row[1]} provisions")

# 3. Sample of DCP text mentioning LEP
print("\n=== 3. SAMPLE DCP TEXT MENTIONING LEP ===")
cur.execute("""
    SELECT LEFT(provision_text, 200), document_id
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%leichhardt%'
           OR document_id ILIKE '%ashfield%'
           OR document_id ILIKE '%marrickville%')
      AND (provision_text ILIKE '%clause 4.%'
           OR provision_text ILIKE '%clause 5.%'
           OR provision_text ILIKE '%lep%')
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"\n  [{row[1][:30]}]")
    print(f"  {row[0]}...")

# 4. What LEP clauses are specifically mentioned?
print("\n=== 4. SPECIFIC LEP CLAUSE REFERENCES IN DCP TEXT ===")
cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%leichhardt%'
           OR document_id ILIKE '%ashfield%'
           OR document_id ILIKE '%marrickville%')
      AND provision_text ~* 'clause [0-9]+\\.[0-9]+'
""")
import re
clause_refs = {}
for row in cur.fetchall():
    matches = re.findall(r'[Cc]lause\s+(\d+\.\d+)', row[0])
    for m in matches:
        clause_refs[m] = clause_refs.get(m, 0) + 1

if clause_refs:
    print("LEP clauses referenced in DCP text:")
    for clause, count in sorted(clause_refs.items(), key=lambda x: -x[1])[:20]:
        print(f"  Clause {clause}: {count}x")

# 5. What's in the current LEP extraction?
print("\n=== 5. CURRENT LEP CONTENT ===")
cur.execute("""
    SELECT
        COALESCE(section_header, 'No section') as section,
        COUNT(*) as provisions
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%lep%'
    GROUP BY section_header
    ORDER BY provisions DESC
    LIMIT 15
""")
print("Inner West LEP sections currently extracted:")
for row in cur.fetchall():
    print(f"  {row[0][:50]}: {row[1]} provisions")

# 6. Check if height/FSR clauses (4.3, 4.4) are extracted
print("\n=== 6. KEY LEP CLAUSES STATUS ===")
key_clauses = ['4.3', '4.4', '4.6', '5.10', '6.1', '6.2']
for clause in key_clauses:
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%lep%'
          AND (provision_text ILIKE %s OR section_header ILIKE %s)
    """, (f'%{clause}%', f'%{clause}%'))
    count = cur.fetchone()[0]
    status = "FOUND" if count > 0 else "MISSING"
    print(f"  Clause {clause}: {status} ({count} provisions)")

# 7. What would LEP extraction enable?
print("\n" + "=" * 70)
print("ANALYSIS SUMMARY")
print("=" * 70)
print("""
LEP is referenced in:
1. Cross-references from DCP/SEPP provisions
2. DCP provision text ("see clause 4.3", "as per LEP")
3. CDC eligibility checks (zone, height, FSR from Planning Portal API)

Current state:
- LEP data comes from NSW Planning Portal API (live queries)
- LEP provisions partially extracted (1,447 provisions)
- Missing: structured clause-by-clause extraction with stable IDs

For CDC pathway:
- Zone, height, FSR already come from Planning Portal API
- LEP extraction NOT required for basic CDC checks

For cross-reference navigation:
- LEP extraction WITH STABLE IDs would enable clickable links
- DCP says "see clause 4.3" -> user could click to see clause 4.3

RECOMMENDATION:
- CDC works without LEP extraction (uses API)
- LEP extraction only needed for cross-reference navigation
- Priority: LOW unless cross-ref navigation is a key feature
""")

conn.close()
