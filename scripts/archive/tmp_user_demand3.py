import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# spatial_overlays by lga_name
cur.execute("SELECT DISTINCT lga_name, COUNT(*) FROM spatial_overlays GROUP BY lga_name ORDER BY COUNT(*) DESC")
print("spatial_overlays by lga_name:")
for r in cur.fetchall():
    print(f"  {r[0]:40s} {r[1]:>5}")

# pre_da_history_reports by council
cur.execute("SELECT DISTINCT council, COUNT(*) FROM pre_da_history_reports GROUP BY council ORDER BY COUNT(*) DESC LIMIT 30")
print("\npre_da_history_reports by council (user searches):")
for r in cur.fetchall():
    print(f"  {str(r[0] or 'NULL'):40s} {r[1]:>5}")

# total pre_da reports
cur.execute("SELECT COUNT(*) FROM pre_da_history_reports")
print(f"\nTotal pre-DA reports generated: {cur.fetchone()[0]}")

conn.close()
