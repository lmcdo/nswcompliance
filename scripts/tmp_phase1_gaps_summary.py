import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Get all LGAs with at least one control
cur.execute("""
SELECT DISTINCT lga FROM dcp_setback_controls WHERE is_current = true ORDER BY lga
""")
all_lgas = [r[0] for r in cur.fetchall()]

# For each LGA, show what Phase 1 types they have
phase1_types = ['front_setback', 'side_setback', 'rear_setback', 'landscaping_min', 'deep_soil_min', 'max_site_coverage']

print("Phase 1 gap analysis (types with 0 = gap):\n")
print(f"{'LGA':28s} {'FR':>3s} {'SI':>3s} {'RE':>3s} {'LS':>3s} {'DS':>3s} {'SC':>3s}")
print("-" * 55)

for lga in all_lgas:
    cur.execute("""
    SELECT control_type, COUNT(*) FROM dcp_setback_controls
    WHERE lga = %s AND is_current = true AND control_type IN %s
    GROUP BY control_type
    """, (lga, tuple(phase1_types)))
    counts = dict(cur.fetchall())
    # Skip inner_west sub-LGAs summary (handled under inner_west)
    vals = " ".join(f"{counts.get(t, 0):>3d}" for t in phase1_types)
    gaps = [t for t in phase1_types if counts.get(t, 0) == 0]
    marker = " ** " + ",".join(t[:2].upper() for t in gaps) if gaps else ""
    print(f"{lga:28s} {vals}{marker}")

print("\n** = missing type. Inner West sub-LGAs (ashfield/leichhardt/marrickville)")
print("   have their data stored under lga='inner_west'.")

conn.close()
