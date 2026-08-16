import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
SELECT lga, control_type, COUNT(*) 
FROM dcp_setback_controls 
WHERE is_current = true
GROUP BY lga, control_type
ORDER BY lga, control_type
""")

from collections import defaultdict
data = defaultdict(lambda: defaultdict(int))
for r in cur.fetchall():
    data[r[0]][r[1]] = r[2]

types = ['front_setback', 'side_setback', 'rear_setback', 'car_parking', 'bicycle_parking',
         'landscaping_min', 'deep_soil_min', 'max_site_coverage', 'tree_canopy_min',
         'max_height', 'separation_from_dwelling', 'communal_open_space_min']
abbr = {'front_setback':'FR', 'side_setback':'SI', 'rear_setback':'RE', 'car_parking':'PK',
        'bicycle_parking':'BP', 'landscaping_min':'LS', 'deep_soil_min':'DS', 'max_site_coverage':'SC',
        'tree_canopy_min':'TC', 'max_height':'HT', 'separation_from_dwelling':'SP',
        'communal_open_space_min':'CO'}

print(f"{'LGA':28s} " + " ".join(f"{abbr[t]:>3s}" for t in types) + "  TOT")
print("-" * 80)
total_rows = 0
for lga in sorted(data.keys()):
    row_total = sum(data[lga].values())
    total_rows += row_total
    vals = " ".join(f"{data[lga].get(t, 0):>3d}" for t in types)
    print(f"{lga:28s} {vals}  {row_total:>3d}")

print(f"\nTotal rows: {total_rows}")
conn.close()
