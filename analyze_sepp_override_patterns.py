#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("SEPP OVERRIDE ANALYSIS")
print("=" * 80)

# 1. Get all SEPP provision IDs and their source documents
cur.execute("""
    SELECT DISTINCT s.sepp_provision_id, rp.document_id
    FROM sepp_lep_overrides s
    LEFT JOIN regulatory_provisions rp ON s.sepp_provision_id::text = rp.id::text
    WHERE rp.document_id IS NOT NULL
    ORDER BY rp.document_id
""")

print("\n=== SEPP Documents with Overrides ===")
sepp_docs = {}
for prov_id, doc_id in cur.fetchall():
    # Extract SEPP name from document_id
    if 'State_Environmental_Planning_Policy' in doc_id:
        # Extract the SEPP name
        parts = doc_id.split('___')[0]
        if parts not in sepp_docs:
            sepp_docs[parts] = 0
        sepp_docs[parts] += 1

for doc, count in sorted(sepp_docs.items(), key=lambda x: x[1], reverse=True):
    sepp_name = doc.replace('State_Environmental_Planning_Policy_', 'SEPP ').replace('_', ' ')
    print(f"  {count:3} overrides - {sepp_name}")

# 2. Most commonly overridden clauses
print("\n=== Most Commonly Overridden LEP Clauses ===")
cur.execute("""
    SELECT lep_clause_reference, override_type, COUNT(*) as count
    FROM sepp_lep_overrides
    GROUP BY lep_clause_reference, override_type
    ORDER BY count DESC
    LIMIT 15
""")

print(f"{'Clause':<15} {'Type':<15} {'Count'}")
print("-" * 45)
for clause, override_type, count in cur.fetchall():
    print(f"{clause:<15} {override_type:<15} {count}")

# 3. Understand what these clauses typically are
print("\n=== Common LEP Clause Numbers (NSW Standard) ===")
standard_clauses = {
    '4': 'Part 4 - Principal development standards',
    '4.3': 'Height of buildings',
    '4.4': 'Floor space ratio',
    '4.6': 'Exceptions to development standards',
    '5': 'Part 5 - Miscellaneous provisions',
    '5.10': 'Heritage conservation',
    '6': 'Part 6 - Urban release areas',
    '3': 'Part 3 - Exempt and complying development',
    '3B': 'Complying development (housing)',
    '3.3': 'Environmentally sensitive areas excluded',
    '2.75': 'Bush fire prone land',
}

for clause, desc in standard_clauses.items():
    cur.execute("""
        SELECT COUNT(*)
        FROM sepp_lep_overrides
        WHERE lep_clause_reference = %s
    """, (clause,))
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  Clause {clause:<10} ({count:2} overrides) - {desc}")

# 4. Check override types
print("\n=== Override Types Distribution ===")
cur.execute("""
    SELECT override_type, COUNT(*) as count
    FROM sepp_lep_overrides
    GROUP BY override_type
    ORDER BY count DESC
""")

for override_type, count in cur.fetchall():
    pct = (count / 91) * 100
    print(f"  {override_type:<20} {count:3} ({pct:5.1f}%)")

# 5. Check which SEPPs typically override which clauses
print("\n=== Top SEPP Override Patterns ===")
cur.execute("""
    SELECT
        s.lep_clause_reference,
        s.override_type,
        rp.document_id,
        COUNT(*) as occurrences
    FROM sepp_lep_overrides s
    LEFT JOIN regulatory_provisions rp ON s.sepp_provision_id::text = rp.id::text
    WHERE rp.document_id IS NOT NULL
    GROUP BY s.lep_clause_reference, s.override_type, rp.document_id
    HAVING COUNT(*) >= 2
    ORDER BY occurrences DESC
    LIMIT 10
""")

print(f"{'Clause':<10} {'Type':<15} {'Count':<8} {'SEPP'}")
print("-" * 80)
for clause, override_type, doc_id, count in cur.fetchall():
    # Shorten SEPP name
    if 'Exempt_and_Complying' in doc_id:
        sepp_name = 'Exempt & Complying Codes'
    elif 'Transport_and_Infrastructure' in doc_id:
        sepp_name = 'Transport & Infrastructure'
    elif 'Housing' in doc_id:
        sepp_name = 'Housing'
    else:
        sepp_name = doc_id.split('___')[0][45:70].replace('_', ' ')

    print(f"{clause:<10} {override_type:<15} {count:<8} {sepp_name}")

conn.close()
