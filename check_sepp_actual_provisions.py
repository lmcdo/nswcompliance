from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== SUSTAINABLE BUILDINGS SEPP 2022 PROVISIONS ===\n")

cur.execute("""
    SELECT id, provision_text, ref_number, provision_type, section_header
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    OR document_id LIKE '%Sustainable Buildings%'
    ORDER BY id
    LIMIT 20
""")

rows = cur.fetchall()
for row in rows:
    print(f"ID: {row[0]}")
    print(f"Ref: {row[2]}")
    print(f"Type: {row[3]}")
    print(f"Section: {row[4]}")
    print(f"Text: {row[1][:200]}...")
    print()

print("="*80 + "\n")
print("SEARCHING FOR CLIMATE ZONE AND BASIX PROVISIONS\n")

cur.execute("""
    SELECT id, provision_text, ref_number, document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable%'
    AND (provision_text ILIKE '%climate zone%' OR provision_text ILIKE '%basix%')
    LIMIT 10
""")

rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"ID: {row[0]} | Ref: {row[2]}")
        print(f"Doc: {row[3]}")
        print(f"Text: {row[1][:300]}...")
        print()
else:
    print("No climate zone or BASIX provisions found")

c.close()