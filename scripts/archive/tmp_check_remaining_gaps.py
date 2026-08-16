import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Inner West controls summary
cur.execute("""
SELECT control_type, dev_type, value_min, value_max, unit, LEFT(condition, 60)
FROM dcp_setback_controls
WHERE lga = 'inner_west' AND is_current = true AND control_type IN ('landscaping_min','deep_soil_min','max_site_coverage')
ORDER BY control_type, dev_type
""")
print("Inner West LS/DS/SC controls:")
for r in cur.fetchall():
    print(f"  {r[0]:20s} {r[1]:28s} min={r[2]} max={r[3]} {r[4]} | {r[5]}")

# Check Campbelltown - did it already have DS before our insert?
cur.execute("""
SELECT id, control_type, dev_type, value_min, unit, LEFT(condition, 50), dcp_version
FROM dcp_setback_controls
WHERE lga = 'campbelltown' AND control_type IN ('deep_soil_min','max_site_coverage') AND is_current = true
ORDER BY control_type, dev_type
""")
print(f"\nCampbelltown DS/SC ({cur.rowcount}):")
for r in cur.fetchall():
    print(f"  id={r[0]} {r[1]:15s} {r[2]:25s} min={r[3]} {r[4]} | {r[5]} | {r[6]}")

# Check CB - did it already have DS/SC before?
cur.execute("""
SELECT id, control_type, dev_type, value_min, unit, LEFT(condition, 50), section_ref
FROM dcp_setback_controls
WHERE lga = 'canterbury_bankstown' AND control_type IN ('deep_soil_min','max_site_coverage','landscaping_min') AND is_current = true
ORDER BY control_type, dev_type
""")
print(f"\nCanterbury-Bankstown LS/DS/SC ({cur.rowcount}):")
for r in cur.fetchall():
    print(f"  id={r[0]} {r[1]:15s} {r[2]:28s} min={r[3]} {r[4]} | {r[5]} | {r[6]}")

conn.close()
