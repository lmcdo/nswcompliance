import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Show LGAs missing landscaping, deep_soil, site_coverage
for ctype in ['landscaping_min', 'deep_soil_min', 'max_site_coverage']:
    cur.execute("""
    SELECT DISTINCT lga FROM dcp_setback_controls
    WHERE control_type = %s AND is_current = true
    """, (ctype,))
    has = {r[0] for r in cur.fetchall()}

    cur.execute("SELECT DISTINCT lga FROM dcp_setback_controls WHERE is_current = true")
    all_lgas = {r[0] for r in cur.fetchall()}

    missing = sorted(all_lgas - has)
    print(f"\n{ctype}: {len(has)} LGAs have it, {len(missing)} missing")
    print(f"  Have: {sorted(has)}")
    print(f"  Missing: {missing}")

# Show existing landscaping/deep_soil/site_coverage data
print("\n\n=== Existing data ===")
for ctype in ['landscaping_min', 'deep_soil_min', 'max_site_coverage']:
    cur.execute("""
    SELECT lga, dev_type, value_min, value_max, unit, LEFT(condition, 50)
    FROM dcp_setback_controls
    WHERE control_type = %s AND is_current = true
    ORDER BY lga, dev_type
    """, (ctype,))
    print(f"\n{ctype} ({cur.rowcount} rows):")
    for r in cur.fetchall():
        print(f"  {r[0]:20s} {r[1]:28s} min={r[2]} max={r[3]} {r[4]} {r[5]}")

conn.close()
