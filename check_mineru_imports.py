from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== CHECKING MINERU IMPORTS ===\n")

# Check how many provisions have mineru extraction
cur.execute("""
    SELECT COUNT(*),
           AVG(LENGTH(provision_text))::int as avg_len,
           MIN(LENGTH(provision_text)) as min_len,
           MAX(LENGTH(provision_text)) as max_len
    FROM regulatory_provisions
    WHERE extraction_method='mineru'
""")

row = cur.fetchone()
print(f"Provisions with extraction_method='mineru': {row[0]}")
print(f"Average text length: {row[1]} chars")
print(f"Min length: {row[2]} chars")
print(f"Max length: {row[3]} chars")

# Show some examples
print(f"\n=== SAMPLE MINERU PROVISIONS ===\n")

cur.execute("""
    SELECT id, ref_number, LENGTH(provision_text) as len, LEFT(provision_text, 200) as preview
    FROM regulatory_provisions
    WHERE extraction_method='mineru'
    ORDER BY LENGTH(provision_text) DESC
    LIMIT 5
""")

for row in cur.fetchall():
    print(f"ID {row[0]}: {row[1]}")
    print(f"  Length: {row[2]} chars")
    print(f"  Preview: {row[3]}...")
    print()

c.close()