from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== CHECKING IF SEPPS LOADED TO DATABASE ===\n")

# Check Sustainable Buildings
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    OR document_id LIKE '%Sustainable Buildings%'
""")
count = cur.fetchone()[0]
print(f"Sustainable Buildings SEPP 2022 provisions: {count}")

# Check Transport & Infrastructure
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE '%Transport_and_Infrastructure%'
    OR document_id LIKE '%Transport and Infrastructure%'
""")
count = cur.fetchone()[0]
print(f"Transport & Infrastructure SEPP 2021 provisions: {count}")

# Check all SEPP documents
print("\n=== ALL DOCUMENTS MATCHING 'SEPP' ===\n")
cur.execute("""
    SELECT document_id, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sepp%'
    GROUP BY document_id
    ORDER BY count DESC
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"{row[1]:4d} provisions: {row[0]}")
else:
    print("No documents with 'SEPP' found")

c.close()