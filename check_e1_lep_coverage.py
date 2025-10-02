from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check what LEP permission data exists for E1
cur.execute("""
    SELECT development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'E1'
    AND source_type NOT ILIKE '%exempt%'
    ORDER BY development_type
""")

print("=== E1 Zone - LEP Permission Coverage ===\n")
results = cur.fetchall()

if results:
    for dev_type, status, source in results:
        print(f"{dev_type:35} {status:15} ({source})")
    print(f"\nTotal: {len(results)} development types with LEP data")
else:
    print("NO LEP permission data for E1")

# Check what Standard Instrument says E1 should permit
print("\n=== What's Missing ===")
print("E1 (National Parks) typically permits:")
print("  - Environmental facilities")
print("  - Information & education facilities  ")
print("  - Some recreation uses")
print("\nE1 typically prohibits:")
print("  - All residential (dwelling house, dual occupancy, etc.)")
print("  - All commercial")
print("  - All industrial")

conn.close()
