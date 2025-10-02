#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

tables = ['regulatory_provisions', 'development_controls', 'development_permissions']

for table in tables:
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
    """)
    print(f"\n=== {table} ===")
    for row in cur.fetchall():
        print(f"  {row[0]:30} {row[1]}")

print("\n=== Sample development_controls ===")
cur.execute("""
    SELECT dc.control_type, dc.control_subtype, dc.value_numeric, dc.unit, 
           rp.development_type, rp.zone, rp.document_id
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    LIMIT 3
""")
for row in cur.fetchall():
    print(f"\n{row[0]}: {row[2]} {row[3]} ({row[1]})")
    print(f"  Dev: {row[4]}, Zone: {row[5]}")
    print(f"  Doc: {row[6][:50]}...")

conn.close()
