from dotenv import load_dotenv; import os, psycopg2
load_dotenv('.env')
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== coverage rows with lga_name='ALL' ===")
cur.execute("SELECT layer_type, feature_count FROM spatial_overlays_coverage WHERE lga_name='ALL' ORDER BY layer_type")
rows = cur.fetchall()
for r in rows: print(f"  {r[0]}: {r[1]} features")
if not rows: print("  NONE")

print("\n=== Which layers are affected by covered_layers bug? ===")
print("(layers with NO _EPI_CONFIRMED path: biodiversity, wetlands, landslide, bushfire, anef)")
for lt in ['biodiversity','wetlands','landslide','bushfire','anef']:
    cur.execute("SELECT COUNT(*), SUM(feature_count) FROM spatial_overlays_coverage WHERE lga_name!='ALL' AND layer_type=%s AND feature_count>0", (lt,))
    r = cur.fetchone()
    cur.execute("SELECT feature_count FROM spatial_overlays_coverage WHERE lga_name='ALL' AND layer_type=%s", (lt,))
    all_row = cur.fetchone()
    print(f"  {lt}: {r[0]} per-LGA entries with data, ALL row: {all_row}")

print("\n=== flood + riparian: EPI-confirmed — covered_layers irrelevant ===")
for lt in ['flood','riparian']:
    cur.execute("SELECT COUNT(*), SUM(feature_count) FROM spatial_overlays_coverage WHERE lga_name!='ALL' AND layer_type=%s AND feature_count>0", (lt,))
    r = cur.fetchone()
    print(f"  {lt}: {r[0]} LGAs with data, {r[1]} total features")

print("\n=== Stale per-LGA entries for global layers (should be 0 after fix) ===")
for lt in ['bushfire','anef','tod_precinct','tod_accelerated','tod_deferred']:
    cur.execute("SELECT COUNT(*) FROM spatial_overlays_coverage WHERE lga_name!='ALL' AND layer_type=%s", (lt,))
    r = cur.fetchone()
    print(f"  {lt}: {r[0]} stale per-LGA rows")

cur.close(); conn.close()
