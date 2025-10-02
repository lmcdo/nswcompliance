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
print("FINDING THE ACTUAL USABLE DATA")
print("="*80)

# 1. Development controls - check schema first
print("\n\n=== 1. DEVELOPMENT_CONTROLS TABLE ===\n")

cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'development_controls'
    ORDER BY ordinal_position;
""")

print("Columns:")
for row in cur.fetchall():
    print(f"  - {row[0]} ({row[1]})")

cur.execute("SELECT COUNT(*) FROM development_controls;")
print(f"\nTotal rows: {cur.fetchone()[0]:,}")

# Sample data
cur.execute("SELECT * FROM development_controls LIMIT 5;")
print(f"\nSample rows:")
rows = cur.fetchall()
if rows:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'development_controls'
        ORDER BY ordinal_position;
    """)
    cols = [r[0] for r in cur.fetchall()]
    print(f"Columns: {', '.join(cols)}")
    for row in rows[:3]:
        print(f"  Row: {row}")

# 2. Zone setback rules
print("\n\n=== 2. ZONE_SETBACK_RULES TABLE ===\n")

cur.execute("SELECT COUNT(*) FROM zone_setback_rules;")
zsr_count = cur.fetchone()[0]
print(f"Total rows: {zsr_count:,}")

if zsr_count > 0:
    cur.execute("""
        SELECT
            zone,
            development_type,
            setback_type,
            minimum_metres,
            LEFT(source_provision, 80) as source
        FROM zone_setback_rules
        WHERE zone = 'R2'
        LIMIT 10;
    """)

    print(f"\n{'Zone':<6} | {'DevType':<20} | {'Type':<15} | {'Value':>6} | Source")
    print("-" * 130)
    for row in cur.fetchall():
        print(f"{row[0]:<6} | {row[1]:<20} | {row[2]:<15} | {row[3]:>6} | {row[4]}")

# 3. Quantitative standards
print("\n\n=== 3. QUANTITATIVE_STANDARDS TABLE ===\n")

cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'quantitative_standards'
    ORDER BY ordinal_position;
""")

print("Columns:")
for row in cur.fetchall():
    print(f"  - {row[0]} ({row[1]})")

cur.execute("SELECT COUNT(*) FROM quantitative_standards;")
qs_count = cur.fetchone()[0]
print(f"\nTotal rows: {qs_count:,}")

if qs_count > 0:
    cur.execute("SELECT * FROM quantitative_standards LIMIT 5;")
    print(f"\nSample rows:")
    for row in cur.fetchall():
        print(f"  {row}")

# 4. Check regulatory_provisions with zone + dev_type
print("\n\n=== 4. REGULATORY_PROVISIONS WITH ZONE ===\n")

cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(DISTINCT zone) as unique_zones,
        COUNT(DISTINCT development_type) as unique_dev_types
    FROM regulatory_provisions
    WHERE zone IS NOT NULL;
""")

row = cur.fetchone()
print(f"Total with zone: {row[0]:,}")
print(f"Unique zones: {row[1]}")
print(f"Unique dev types: {row[2]}")

# Sample zones
cur.execute("""
    SELECT DISTINCT zone
    FROM regulatory_provisions
    WHERE zone IS NOT NULL
    ORDER BY zone
    LIMIT 20;
""")

print(f"\nZones in database:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

# 5. Sample R2 + dwelling_house provisions
print("\n\n=== 5. SAMPLE: R2 + DWELLING_HOUSE ===\n")

cur.execute("""
    SELECT
        id,
        provision_type,
        LEFT(provision_text, 100) as text,
        zone,
        development_type
    FROM regulatory_provisions
    WHERE zone = 'R2'
      AND development_type IS NOT NULL
      AND provision_type LIKE 'provision_%'
    LIMIT 15;
""")

print(f"{'ID':>6} | {'Type':<30} | {'Zone':<6} | {'DevType':<18} | Text")
print("-" * 170)
for row in cur.fetchall():
    print(f"{row[0]:>6} | {row[1]:<30} | {row[3]:<6} | {row[4]:<18} | {row[2]}")

# 6. Check if provisions have numeric values extracted
print("\n\n=== 6. PROVISIONS WITH EXTRACTED VALUES ===\n")

cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND (
          column_name LIKE '%value%'
          OR column_name LIKE '%numeric%'
          OR column_name LIKE '%metres%'
          OR column_name LIKE '%number%'
      )
    ORDER BY column_name;
""")

value_cols = cur.fetchall()
if value_cols:
    print("Value columns in regulatory_provisions:")
    for row in value_cols:
        print(f"  - {row[0]}")
else:
    print("No extracted value columns found")

# 7. Check development_permissions
print("\n\n=== 7. DEVELOPMENT_PERMISSIONS TABLE ===\n")

cur.execute("SELECT COUNT(*) FROM development_permissions WHERE zone = 'R2';")
print(f"Total permissions for R2: {cur.fetchone()[0]:,}")

cur.execute("""
    SELECT DISTINCT development_type
    FROM development_permissions
    WHERE zone = 'R2'
    ORDER BY development_type;
""")

print(f"\nDevelopment types for R2:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

cur.close()
conn.close()

print("\n" + "="*80)
print("DATA AUDIT COMPLETE")
print("="*80)