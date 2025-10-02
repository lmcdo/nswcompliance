#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# NSW LEPs have land use tables in schedules or specific sections
# Look for Schedule references
cur.execute("""
    SELECT ref_number, section_header, LENGTH(provision_text), provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%lep%'
    AND (
        ref_number ILIKE 'schedule%'
        OR section_header ILIKE '%land use table%'
        OR section_header ILIKE '%additional permitted%'
        OR section_header ILIKE '%prohibited%'
        OR provision_text ILIKE '%land use table%'
    )
    ORDER BY ref_number
    LIMIT 10
""")

print("=== LEP Land Use Table References ===\n")
results = cur.fetchall()
if results:
    for ref, header, length, text in results:
        print(f"Ref: {ref}")
        print(f"Header: {header}")
        print(f"Length: {length} chars")
        print(f"Preview: {text[:200] if text else 'N/A'}...")
        print()
else:
    print("No schedule/land use table references found in LEP")

# Check what we currently have for E1 zone
print("\n=== Current E1 Zone Coverage ===")
cur.execute("""
    SELECT development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'E1'
    ORDER BY source_type, development_type
""")

for dev_type, status, source in cur.fetchall():
    print(f"{dev_type:40} {status:15} ({source})")

# The real question: where did nsw_standard data come from?
print("\n=== Where did 'nsw_standard' data come from? ===")
cur.execute("""
    SELECT DISTINCT zone, COUNT(*) 
    FROM development_permissions
    WHERE source_type = 'nsw_standard'
    GROUP BY zone
    ORDER BY zone
""")

print("Zones with nsw_standard data:")
for zone, count in cur.fetchall():
    print(f"  {zone}: {count} development types")

conn.close()
