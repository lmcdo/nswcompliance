from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check E1 zone permissions
cur.execute("""
    SELECT zone, development_type, permission_status, source_type, conditions
    FROM development_permissions
    WHERE zone = 'E1'
    ORDER BY development_type
""")

print("=== E1 Zone Permissions in Database ===\n")
for row in cur.fetchall():
    print(f"Zone: {row[0]}")
    print(f"Dev Type: {row[1]}")
    print(f"Status: {row[2]}")
    print(f"Source: {row[3]}")
    print(f"Conditions: {row[4]}")
    print()

# Check what provisions led to this
cur.execute("""
    SELECT id, document_id, ref_number, zone, development_type, provision_text
    FROM regulatory_provisions
    WHERE zone = 'E1'
    AND (document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%')
    LIMIT 5
""")

print("=== Sample E1 Provisions ===\n")
for row in cur.fetchall():
    print(f"ID: {row[0]}")
    print(f"Doc: {row[1][:50]}...")
    print(f"Ref: {row[2]}")
    print(f"Zone: {row[3]}")
    print(f"Dev Type: {row[4]}")
    print(f"Text: {row[5][:150]}...")
    print()

# Check standard LEP permissions for E1
cur.execute("""
    SELECT zone, development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'E1'
    AND source_type NOT ILIKE '%exempt%'
    LIMIT 10
""")

print("=== E1 Standard LEP Permissions ===\n")
results = cur.fetchall()
if results:
    for row in results:
        print(f"{row[0]} + {row[1]} = {row[2]} ({row[3]})")
else:
    print("No standard LEP permissions for E1")

conn.close()
