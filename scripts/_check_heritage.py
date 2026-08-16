import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("""
    SELECT value, COUNT(*)
    FROM spatial_overlays
    WHERE layer_type = 'heritage'
    GROUP BY value
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")
print("Heritage value distribution:")
for row in cur.fetchall():
    print(f"  {row[0]!r}: {row[1]}")

cur.execute("SELECT COUNT(*) FROM spatial_overlays WHERE layer_type='heritage' AND value IS NULL")
null_count = cur.fetchone()[0]
print(f"\nNULL values remaining: {null_count}")

# Sample Inner West HCA rows
cur.execute("""
    SELECT value, instrument_key
    FROM spatial_overlays
    WHERE layer_type = 'heritage' AND lga_name = 'INNER WEST'
    LIMIT 5
""")
print("\nSample Inner West heritage rows:")
for row in cur.fetchall():
    print(f"  value={row[0]!r}  instrument={row[1]!r}")

cur.close()
conn.close()
