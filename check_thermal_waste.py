from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== THERMAL ENERGY FROM WASTE PROVISIONS ===\n")

# Get the 3 provisions found
cur.execute("SELECT id, provision_text, ref_number, document_id FROM regulatory_provisions WHERE id IN (18945, 19101, 19195)")
rows = cur.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"Ref: {row[2]}")
    print(f"Document: {row[3]}")
    print(f"Text:\n{row[1][:800]}")
    print("\n" + "="*80 + "\n")

c.close()