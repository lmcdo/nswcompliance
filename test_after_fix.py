import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

print("TESTING API QUERY AFTER FIXES")
print("="*70)

cur.execute("""
    SELECT
        dc.control_type,
        dc.control_subtype,
        dc.value_numeric,
        dc.unit
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE rp.zone = 'R2'
      AND dc.control_type IN ('height', 'setback', 'parking', 'fsr')
      AND dc.confidence_score::numeric > 0.75
      AND dc.value_numeric IS NOT NULL
    ORDER BY dc.confidence_score::numeric DESC
    LIMIT 15;
""")

print("\n15 controls from API query:")
print(f"{'Type':<12} {'Subtype':<15} {'Value':>8} {'Unit':<10}")
print("-"*50)

all_good = True
for row in cur.fetchall():
    val = float(row[2])
    print(f"{row[0]:<12} {(row[1] or 'N/A'):<15} {row[2]:>8} {(row[3] or 'N/A'):<10}")

    # Check if value is reasonable
    if row[0] == 'height' and val > 50:
        print(f"  WARNING: Height {val}m seems too large!")
        all_good = False
    if row[0] == 'setback' and val > 20:
        print(f"  WARNING: Setback {val}m seems too large!")
        all_good = False

cur.close()
conn.close()

print("\n" + "="*70)
if all_good:
    print("[SUCCESS] All values look reasonable!")
else:
    print("[WARNING] Some suspicious values remain")