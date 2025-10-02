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
print("DEVELOPMENT_CONTROLS TABLE - THE ACTUAL EXTRACTED DATA")
print("="*80)

# 1. Check what control types exist
print("\n\n=== Control Types Distribution ===\n")

cur.execute("""
    SELECT
        control_type,
        control_subtype,
        COUNT(*) as count,
        AVG(CAST(confidence_score AS NUMERIC)) as avg_confidence
    FROM development_controls
    WHERE control_type IS NOT NULL
    GROUP BY control_type, control_subtype
    ORDER BY count DESC
    LIMIT 30;
""")

print(f"{'Control Type':<20} | {'Subtype':<25} | {'Count':>6} | {'Avg Conf':>8}")
print("-" * 75)
for row in cur.fetchall():
    conf = f"{row[3]:.2f}" if row[3] else "N/A"
    print(f"{row[0]:<20} | {(row[1] or 'N/A'):<25} | {row[2]:>6} | {conf:>8}")

# 2. Check how provisions link to controls
print("\n\n=== Link Between Provisions and Controls ===\n")

cur.execute("""
    SELECT
        dc.control_type,
        dc.value_numeric,
        dc.unit,
        rp.zone,
        rp.development_type,
        LEFT(rp.provision_text, 80) as text
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE rp.zone = 'R2'
      AND dc.control_type IN ('height', 'setback', 'parking')
    LIMIT 20;
""")

print(f"{'Type':<12} | {'Value':>6} | {'Unit':<10} | {'Zone':<6} | {'DevType':<18} | Text")
print("-" * 140)
for row in cur.fetchall():
    dev_type = (row[4] or 'N/A')[:18]
    print(f"{row[0]:<12} | {row[1]:>6} | {(row[2] or 'N/A'):<10} | {row[3]:<6} | {dev_type:<18} | {row[5]}")

# 3. Count how many controls link to R2 provisions
print("\n\n=== Controls for R2 Zone ===\n")

cur.execute("""
    SELECT
        dc.control_type,
        COUNT(*) as count
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE rp.zone = 'R2'
    GROUP BY dc.control_type
    ORDER BY count DESC;
""")

print(f"{'Control Type':<20} | {'Count':>6}")
print("-" * 30)
for row in cur.fetchall():
    print(f"{row[0]:<20} | {row[1]:>6}")

# 4. Check zone_setback_rules actual schema
print("\n\n=== ZONE_SETBACK_RULES TABLE ===\n")

cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'zone_setback_rules'
    ORDER BY ordinal_position;
""")

print("Columns:")
for row in cur.fetchall():
    print(f"  - {row[0]} ({row[1]})")

cur.execute("SELECT * FROM zone_setback_rules LIMIT 6;")
print(f"\nAll {cur.rowcount} rows:")
for row in cur.fetchall():
    print(f"  {row}")

# 5. Check quantitative_standards
print("\n\n=== QUANTITATIVE_STANDARDS TABLE ===\n")

cur.execute("SELECT * FROM quantitative_standards LIMIT 10;")
rows = cur.fetchall()
print(f"Sample rows: {len(rows)}")
for row in rows[:5]:
    print(f"  {row}")

cur.close()
conn.close()

print("\n" + "="*80)
print("SUMMARY: development_controls table has extracted numeric values!")
print("Join with regulatory_provisions on provision_id to get zone + dev_type")
print("="*80)