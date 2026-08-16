"""Check what data is in the database after restore."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Check counts
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(document_id) as has_document_id,
        COUNT(v2_dcp_layer) as has_layer,
        COUNT(CASE WHEN document_id ILIKE '%Leichhardt%' THEN 1 END) as leichhardt_provisions,
        COUNT(v2_is_actionable) as has_actionable_value
    FROM regulatory_provisions
""")
row = cur.fetchone()

print("\n" + "="*70)
print("DATABASE CONTENT CHECK")
print("="*70)
print(f"\nTotal provisions: {row[0]:,}")
print(f"Provisions with document_id: {row[1]:,}")
print(f"Provisions with v2_dcp_layer: {row[2]:,}")
print(f"Leichhardt provisions: {row[3]:,}")
print(f"Provisions with v2_is_actionable: {row[4]:,}")

# Check sample data
cur.execute("""
    SELECT id, document_id, v2_dcp_layer, v2_is_actionable, LEFT(provision_text, 60)
    FROM regulatory_provisions
    LIMIT 5
""")

print("\nSample provisions:")
for row in cur.fetchall():
    print(f"  ID={row[0]}, doc={row[1]}, layer={row[2]}, actionable={row[3]}")
    print(f"    text: {row[4]}...")

cur.close()
conn.close()
