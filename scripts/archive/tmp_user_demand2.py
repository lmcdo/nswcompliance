import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Check spatial_overlays columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'spatial_overlays' ORDER BY ordinal_position")
print("spatial_overlays columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check feedback_analytics
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'feedback_analytics' ORDER BY ordinal_position")
print("\nfeedback_analytics columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check pre_da_history_reports for address lookups
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'pre_da_history_reports' ORDER BY ordinal_position")
print("\npre_da_history_reports columns:")
for r in cur.fetchall():
    print(f"  {r[0]}")

conn.close()
