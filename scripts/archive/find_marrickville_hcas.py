"""Find Marrickville HCAs."""

import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT')
)
cur = conn.cursor()

print("Searching for Marrickville HCAs with 'HCA' prefix...")

cur.execute("""
    SELECT h_id, h_name, db_slug, lga_name
    FROM heritage_conservation_areas
    WHERE h_id LIKE 'HCA%'
       OR h_id LIKE 'hca%'
    ORDER BY h_id
    LIMIT 50;
""")

results = cur.fetchall()
print(f"\nFound {len(results)} HCAs with 'HCA' prefix:\n")
for h_id, h_name, db_slug, lga in results[:20]:
    # Truncate to avoid unicode errors
    name_safe = h_name[:40] if h_name else "None"
    slug_safe = db_slug[:30] if db_slug else "None"
    print(f"{h_id:10} | {name_safe:40} | {slug_safe:30}")

# Check if "HCA 10" (with space) exists
print("\n" + "=" * 80)
print("Checking for 'HCA 10' with space...")

cur.execute("""
    SELECT h_id, h_name, db_slug
    FROM heritage_conservation_areas
    WHERE h_id = 'HCA 10'
       OR h_id = 'HCA10'
       OR h_id = 'hca 10'
       OR h_id = 'hca10';
""")

results = cur.fetchall()
if results:
    print(f"Found {len(results)} matches:")
    for h_id, h_name, db_slug in results:
        print(f"  h_id: {h_id}")
        print(f"  db_slug: {db_slug}")
else:
    print("No matches for 'HCA 10' or 'HCA10'")

cur.close()
conn.close()
