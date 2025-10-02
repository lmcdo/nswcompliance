import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

print("\n=== KG Entities Sample ===\n")
cur.execute("""
  SELECT
    entity_type,
    entity_name,
    LEFT(entity_description, 60) as description,
    document_id,
    section_header
  FROM kg_entities
  LIMIT 10;
""")

print(f"{'Type':<25} | {'Name':<30} | {'Description':<60}")
print("-" * 120)
for row in cur.fetchall():
    print(f"{row[0]:<25} | {row[1]:<30} | {row[2]}")

print("\n\n=== KG Relationships Sample ===\n")
cur.execute("""
  SELECT
    predicate,
    LEFT(subject_text, 40) as subject,
    LEFT(object_text, 40) as object,
    confidence_score,
    document_id
  FROM kg_relationships
  LIMIT 10;
""")

print(f"{'Predicate':<30} | {'Subject':<40} | {'Object':<40} | Score")
print("-" * 120)
for row in cur.fetchall():
    print(f"{row[0]:<30} | {row[1]:<40} | {row[2]:<40} | {row[3]}")

print("\n\n=== Entity Types Distribution ===\n")
cur.execute("""
  SELECT entity_type, COUNT(*)
  FROM kg_entities
  GROUP BY entity_type
  ORDER BY COUNT(*) DESC
  LIMIT 20;
""")

print(f"{'Entity Type':<50} | Count")
print("-" * 70)
for row in cur.fetchall():
    print(f"{row[0]:<50} | {row[1]}")

print("\n\n=== Relationship Types Distribution ===\n")
cur.execute("""
  SELECT predicate, COUNT(*)
  FROM kg_relationships
  GROUP BY predicate
  ORDER BY COUNT(*) DESC
  LIMIT 20;
""")

print(f"{'Relationship Type':<50} | Count")
print("-" * 70)
for row in cur.fetchall():
    print(f"{row[0]:<50} | {row[1]}")

print("\n\n=== Can We Query for R2 + Dwelling House? ===\n")

# Check if we have zone entities
cur.execute("""
  SELECT entity_name, COUNT(*)
  FROM kg_entities
  WHERE entity_name LIKE '%R2%' OR entity_name LIKE '%zone%'
  GROUP BY entity_name
  LIMIT 10;
""")

print("\nZone-related entities:")
for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]}")

# Check if we have development type entities
cur.execute("""
  SELECT entity_name, COUNT(*)
  FROM kg_entities
  WHERE entity_name LIKE '%dwelling%' OR entity_name LIKE '%house%'
  GROUP BY entity_name
  LIMIT 10;
""")

print("\nDwelling-related entities:")
for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]}")

print("\n\n=== Link Between Provisions and KG ===\n")

# Check if provisions reference entity IDs
cur.execute("""
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'regulatory_provisions'
    AND (
      column_name LIKE '%entity%'
      OR column_name LIKE '%kg%'
    )
  ORDER BY ordinal_position;
""")

print("\nProvisions columns linking to KG:")
cols = cur.fetchall()
if cols:
    for row in cols:
        print(f"  - {row[0]} ({row[1]})")
else:
    print("  (No direct links found)")

print("\n\n=== Are Provision IDs Referenced in KG? ===\n")

cur.execute("""
  SELECT
    original_ref_type,
    COUNT(*) as count
  FROM kg_entities
  WHERE original_ref_id IS NOT NULL
  GROUP BY original_ref_type;
""")

print("\nEntity refs to provisions:")
for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]}")

cur.close()
conn.close()