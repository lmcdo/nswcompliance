import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Check what inner_west already has in dcp_setback_controls
for lga in ['inner_west', 'ashfield', 'leichhardt', 'marrickville']:
    cur.execute("""
    SELECT control_type, dev_type, value_min, value_max, unit, LEFT(condition, 50)
    FROM dcp_setback_controls
    WHERE lga = %s AND is_current = true
    ORDER BY control_type, dev_type
    """, (lga,))
    print(f"\n{lga} structured controls ({cur.rowcount}):")
    for r in cur.fetchall():
        print(f"  {r[0]:20s} {r[1]:28s} min={r[2]} max={r[3]} {r[4]} {r[5]}")

# Check regulatory_provisions for landscaping text
for lga in ['inner_west', 'ashfield', 'leichhardt', 'marrickville']:
    cur.execute("""
    SELECT id, v2_topic, LEFT(provision_text, 120)
    FROM regulatory_provisions
    WHERE source_council = %s AND provision_text ILIKE '%%landscap%%' AND v2_has_numeric_value = true
    LIMIT 10
    """, (lga,))
    if cur.rowcount > 0:
        print(f"\n{lga} landscaping provisions with numeric values ({cur.rowcount}):")
        for r in cur.fetchall():
            print(f"  id={r[0]} topic={r[1]} | {r[2]}")

conn.close()
