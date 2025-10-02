import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

print("\n=== Provision Types in R2 Zone ===\n")
cur.execute("""
  SELECT document_category, provision_type, COUNT(*)
  FROM provisions_with_category
  WHERE zone = 'R2'
    AND provision_type IS NOT NULL
    AND provision_type != ''
  GROUP BY document_category, provision_type
  ORDER BY document_category, COUNT(*) DESC
  LIMIT 30;
""")

print(f"{'Document Category':<20} | {'Provision Type':<35} | Count")
print("-" * 70)
for row in cur.fetchall():
    print(f"{row[0]:<20} | {row[1]:<35} | {row[2]}")

print("\n\n=== Total by Document Category (zone R2, with dev type filter) ===\n")
cur.execute("""
  SELECT
    document_category,
    COUNT(*) as total,
    COUNT(CASE WHEN development_type = 'dwelling_house' OR development_type IS NULL THEN 1 END) as dwelling_house_applicable
  FROM provisions_with_category
  WHERE zone = 'R2'
    AND provision_type IS NOT NULL
    AND provision_type != ''
  GROUP BY document_category
  ORDER BY total DESC;
""")

print(f"{'Document Category':<20} | {'Total':<10} | Dwelling House Applicable")
print("-" * 60)
for row in cur.fetchall():
    print(f"{row[0]:<20} | {row[1]:<10} | {row[2]}")

print("\n\n=== Sample of 10 provisions returned by API query ===\n")
cur.execute("""
  SELECT
    document_category,
    provision_type,
    LEFT(provision_text, 50) as text_preview,
    ref_number
  FROM provisions_with_category
  WHERE zone = 'R2'
    AND provision_type IS NOT NULL
    AND provision_type != ''
    AND (
      'dwelling_house'::text IS NULL
      OR development_type = 'dwelling_house'::text
      OR development_type IS NULL
    )
  ORDER BY ref_number
  LIMIT 10;
""")

print(f"{'Category':<15} | {'Type':<25} | {'Ref':<10} | Preview")
print("-" * 100)
for row in cur.fetchall():
    print(f"{row[0]:<15} | {row[1]:<25} | {row[3]:<10} | {row[2]}")

cur.close()
conn.close()