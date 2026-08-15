import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# For each target LGA, find setback provisions
target_lgas = ['bayside', 'georges_river', 'inner_west', 'ku_ring_gai', 'parramatta', 
               'randwick', 'sutherland_shire', 'waverley', 'woollahra']

for lga in target_lgas:
    cur.execute("""
    SELECT COUNT(*), 
           COUNT(*) FILTER (WHERE v2_has_numeric_value = true)
    FROM regulatory_provisions
    WHERE source_council = %s AND v2_topic = 'setbacks' AND is_current = true
    """, (lga,))
    r = cur.fetchone()
    
    # Also check what chapters are registered
    cur.execute("""
    SELECT COUNT(*) FROM dcp_chapter_registry WHERE council = %s AND is_active = true
    """, (lga,))
    ch = cur.fetchone()
    
    # Check existing setback controls
    cur.execute("""
    SELECT control_type, COUNT(*) FROM dcp_setback_controls 
    WHERE lga = %s AND control_type IN ('front_setback','side_setback','rear_setback')
    GROUP BY control_type
    """, (lga,))
    existing = {row[0]: row[1] for row in cur.fetchall()}
    
    print(f"{lga:25s} provisions={r[0]:3d} (numeric={r[1]:3d}) chapters={ch[0]:3d} existing_setbacks={existing}")

conn.close()
