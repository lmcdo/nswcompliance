from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== CHECKING FOR SEPP AMENDMENTS IN DATABASE ===\n")

# List of SEPPs and amendments to check
sepps_to_check = [
    ("Thermal Energy from Waste", "Transport and Infrastructure"),
    ("Sustainable Buildings", "BASIX"),
    ("Climate Zones", "Sustainable Buildings"),
]

print("1. THERMAL ENERGY FROM WASTE (Transport & Infrastructure Amendment 2022)\n")
cur.execute("""
    SELECT id, provision_text, ref_number, document_id, provision_type
    FROM regulatory_provisions
    WHERE (provision_text ILIKE '%thermal%energy%waste%'
       OR provision_text ILIKE '%thermal%waste%prohibition%'
       OR document_id ILIKE '%thermal%energy%waste%')
    AND document_id ILIKE '%transport%'
    LIMIT 10
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"ID: {row[0]} | Ref: {row[2]} | Type: {row[4]}")
        print(f"Doc: {row[3]}")
        print(f"Text: {row[1][:200]}...")
        print()
else:
    print("NOT FOUND\n")

print("="*80 + "\n")

print("2. SUSTAINABLE BUILDINGS SEPP 2022 (BASIX/Climate Zones)\n")
cur.execute("""
    SELECT id, provision_text, ref_number, document_id, provision_type
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sustainable%building%'
    OR provision_text ILIKE '%basix%'
    OR provision_text ILIKE '%climate%zone%'
    LIMIT 15
""")
rows = cur.fetchall()
if rows:
    print(f"Found {len(rows)} provisions:\n")
    for row in rows:
        print(f"ID: {row[0]} | Ref: {row[2]} | Type: {row[4]}")
        print(f"Doc: {row[3]}")
        print(f"Text: {row[1][:150]}...")
        print()
else:
    print("NOT FOUND\n")

print("="*80 + "\n")

print("3. ALL UNIQUE SEPP DOCUMENTS IN DATABASE\n")
cur.execute("""
    SELECT DISTINCT document_id, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sepp%'
    GROUP BY document_id
    ORDER BY count DESC
""")
rows = cur.fetchall()
print(f"Found {len(rows)} unique SEPP documents:\n")
for row in rows[:20]:
    print(f"{row[1]:4d} provisions: {row[0]}")

c.close()