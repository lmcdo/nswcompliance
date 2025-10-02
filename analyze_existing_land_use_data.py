#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check extraction methods used
cur.execute("""
    SELECT 
        source_type,
        COUNT(*) as count,
        COUNT(DISTINCT zone) as zones,
        COUNT(DISTINCT development_type) as dev_types
    FROM development_permissions
    GROUP BY source_type
    ORDER BY count DESC
""")

print("=== Current development_permissions Data ===\n")
print(f"{'Source':30} {'Records':10} {'Zones':10} {'Dev Types':10}")
print("-" * 60)
for row in cur.fetchall():
    print(f"{row[0]:30} {row[1]:10} {row[2]:10} {row[3]:10}")

# Check if we have table_parsing_results
cur.execute("SELECT COUNT(*) FROM table_parsing_results")
table_count = cur.fetchone()[0]
print(f"\n=== table_parsing_results table ===")
print(f"Records: {table_count}")

if table_count > 0:
    cur.execute("""
        SELECT document_id, table_type, extraction_method, COUNT(*)
        FROM table_parsing_results
        GROUP BY document_id, table_type, extraction_method
        LIMIT 10
    """)
    print("\nSample table extractions:")
    for row in cur.fetchall():
        print(f"  {row[0][:50]}... | {row[1]} | {row[2]} | {row[3]} rows")

# Check for LEP land use table provisions
cur.execute("""
    SELECT COUNT(*) 
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%lep%'
    AND (section_header ILIKE '%land use%' OR section_header ILIKE '%table%')
""")

lep_table_provisions = cur.fetchone()[0]
print(f"\n=== LEP provisions with 'land use' or 'table' ===")
print(f"Count: {lep_table_provisions}")

if lep_table_provisions > 0:
    cur.execute("""
        SELECT ref_number, section_header, LENGTH(provision_text)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%lep%'
        AND (section_header ILIKE '%land use%' OR section_header ILIKE '%table%')
        LIMIT 5
    """)
    print("\nSamples:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} ({row[2]} chars)")

conn.close()
