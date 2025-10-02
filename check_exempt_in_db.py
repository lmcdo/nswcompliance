#!/usr/bin/env python3
"""Check if Exempt and Complying codes are in database"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check for exempt/complying provisions
cur.execute("""
    SELECT
        document_id,
        COUNT(*) as count,
        extraction_method,
        AVG(LENGTH(provision_text))::int as avg_len
    FROM regulatory_provisions
    WHERE document_id ILIKE '%exempt%'
       OR document_id ILIKE '%complying%'
    GROUP BY document_id, extraction_method
    ORDER BY count DESC
    LIMIT 10
""")

print("\n=== Exempt/Complying Provisions in Database ===\n")
rows = cur.fetchall()

if not rows:
    print("❌ NO provisions found with 'exempt' or 'complying' in document_id")
else:
    for row in rows:
        doc_id, count, method, avg_len = row
        print(f"{doc_id[:80]}")
        print(f"  Count: {count}")
        print(f"  Method: {method}")
        print(f"  Avg length: {avg_len} chars")
        print()

# Check total SEPP provisions by extraction method
cur.execute("""
    SELECT
        extraction_method,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%state%environmental%'
    GROUP BY extraction_method
""")

print("\n=== SEPP Provisions by Extraction Method ===\n")
for row in cur.fetchall():
    method, count = row
    print(f"{method}: {count:,} provisions")

conn.close()
