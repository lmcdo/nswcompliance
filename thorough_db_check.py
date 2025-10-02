import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

print("\n" + "="*80)
print("COMPLETE DATABASE AUDIT - FINDING THE ACTUAL DATA")
print("="*80)

# 1. Check regulatory_provisions table thoroughly
print("\n\n=== 1. REGULATORY_PROVISIONS TABLE ===\n")

cur.execute("SELECT COUNT(*) FROM regulatory_provisions;")
total = cur.fetchone()[0]
print(f"Total provisions: {total:,}")

cur.execute("""
    SELECT
        document_id,
        COUNT(*) as count,
        COUNT(DISTINCT provision_type) as unique_types
    FROM regulatory_provisions
    WHERE provision_text IS NOT NULL
    GROUP BY document_id
    ORDER BY count DESC
    LIMIT 20;
""")
print(f"\n{'Document ID':<60} | {'Count':>8} | Types")
print("-" * 80)
for row in cur.fetchall():
    print(f"{row[0]:<60} | {row[1]:>8,} | {row[2]}")

# 2. Check for specific setback/height provisions
print("\n\n=== 2. ACTUAL SETBACK/HEIGHT PROVISIONS ===\n")

cur.execute("""
    SELECT
        provision_type,
        COUNT(*) as count,
        COUNT(CASE WHEN zone IS NOT NULL THEN 1 END) as with_zone,
        COUNT(CASE WHEN development_type IS NOT NULL THEN 1 END) as with_dev_type
    FROM regulatory_provisions
    WHERE provision_type ILIKE '%setback%'
       OR provision_type ILIKE '%height%'
       OR provision_type ILIKE '%parking%'
    GROUP BY provision_type
    ORDER BY count DESC
    LIMIT 20;
""")

print(f"{'Provision Type':<40} | {'Total':>8} | {'W/Zone':>8} | {'W/DevType':>8}")
print("-" * 80)
for row in cur.fetchall():
    print(f"{row[0]:<40} | {row[1]:>8} | {row[2]:>8} | {row[3]:>8}")

# 3. Sample actual provisions with zone + dev type
print("\n\n=== 3. SAMPLE PROVISIONS WITH ZONE + DEV_TYPE ===\n")

cur.execute("""
    SELECT
        id,
        provision_type,
        zone,
        development_type,
        LEFT(provision_text, 80) as text_preview
    FROM regulatory_provisions
    WHERE zone = 'R2'
      AND development_type = 'dwelling_house'
      AND (
          provision_type ILIKE '%setback%'
          OR provision_type ILIKE '%height%'
          OR provision_type ILIKE '%parking%'
      )
    LIMIT 10;
""")

print(f"{'ID':>6} | {'Type':<30} | {'Zone':<6} | {'DevType':<15} | Preview")
print("-" * 120)
for row in cur.fetchall():
    print(f"{row[0]:>6} | {row[1]:<30} | {row[2]:<6} | {row[3]:<15} | {row[4]}")

# 4. Check development_controls table
print("\n\n=== 4. DEVELOPMENT_CONTROLS TABLE ===\n")

cur.execute("SELECT COUNT(*) FROM development_controls;")
dc_count = cur.fetchone()[0]
print(f"Total development_controls: {dc_count:,}")

if dc_count > 0:
    cur.execute("""
        SELECT
            control_type,
            COUNT(*) as count,
            COUNT(CASE WHEN zone IS NOT NULL THEN 1 END) as with_zone
        FROM development_controls
        GROUP BY control_type
        ORDER BY count DESC
        LIMIT 15;
    """)

    print(f"\n{'Control Type':<40} | {'Count':>8} | {'W/Zone':>8}")
    print("-" * 65)
    for row in cur.fetchall():
        print(f"{row[0]:<40} | {row[1]:>8} | {row[2]:>8}")

    # Sample
    cur.execute("""
        SELECT
            control_type,
            zone,
            development_type,
            LEFT(control_value, 50) as value
        FROM development_controls
        WHERE zone = 'R2'
        LIMIT 10;
    """)

    print(f"\n\nSample R2 controls:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[3]} (zone: {row[1]}, dev: {row[2]})")

# 5. Check quantitative_standards table
print("\n\n=== 5. QUANTITATIVE_STANDARDS TABLE ===\n")

cur.execute("SELECT COUNT(*) FROM quantitative_standards;")
qs_count = cur.fetchone()[0]
print(f"Total quantitative_standards: {qs_count:,}")

if qs_count > 0:
    cur.execute("""
        SELECT
            standard_type,
            COUNT(*) as count
        FROM quantitative_standards
        GROUP BY standard_type
        ORDER BY count DESC
        LIMIT 15;
    """)

    print(f"\n{'Standard Type':<40} | {'Count':>8}")
    print("-" * 55)
    for row in cur.fetchall():
        print(f"{row[0]:<40} | {row[1]:>8}")

# 6. Check zone_setback_rules table
print("\n\n=== 6. ZONE_SETBACK_RULES TABLE ===\n")

cur.execute("SELECT COUNT(*) FROM zone_setback_rules;")
zsr_count = cur.fetchone()[0]
print(f"Total zone_setback_rules: {zsr_count:,}")

if zsr_count > 0:
    cur.execute("""
        SELECT
            zone,
            development_type,
            setback_type,
            minimum_metres,
            LEFT(source_provision, 60) as source
        FROM zone_setback_rules
        WHERE zone = 'R2'
        LIMIT 15;
    """)

    print(f"\n{'Zone':<6} | {'DevType':<20} | {'Type':<15} | {'Value':>6} | Source")
    print("-" * 120)
    for row in cur.fetchall():
        print(f"{row[0]:<6} | {row[1]:<20} | {row[2]:<15} | {row[3]:>6} | {row[4]}")

# 7. Check if there are tables with "extracted" or "semantic" in name
print("\n\n=== 7. TABLES WITH 'EXTRACTED' OR 'SEMANTIC' ===\n")

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND (
          table_name LIKE '%extract%'
          OR table_name LIKE '%semantic%'
          OR table_name LIKE '%rule%'
          OR table_name LIKE '%control%'
      )
    ORDER BY table_name;
""")

for row in cur.fetchall():
    table_name = row[0]
    cur.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cur.fetchone()[0]
    print(f"  {table_name:<50} | {count:>8,} rows")

# 8. Check documents table - are extraction JSONs referenced?
print("\n\n=== 8. DOCUMENTS TABLE - JSON REFERENCES ===\n")

cur.execute("""
    SELECT
        id,
        document_type,
        metadata
    FROM documents
    WHERE metadata IS NOT NULL
      AND metadata::text LIKE '%json%'
    LIMIT 5;
""")

docs = cur.fetchall()
if docs:
    print("Documents with JSON metadata:")
    for row in docs:
        print(f"  {row[0]}: {row[1]}")
        print(f"    Metadata: {str(row[2])[:100]}")
else:
    print("No documents with JSON metadata found")

cur.close()
conn.close()

print("\n\n" + "="*80)
print("AUDIT COMPLETE")
print("="*80)