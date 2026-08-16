"""Find HCA 10 in heritage_conservation_areas table."""

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

# Search for HCA 10 variations
print("Searching for HCA 10 variations...")

cur.execute("""
    SELECT h_id, h_name, db_slug
    FROM heritage_conservation_areas
    WHERE h_id ILIKE '%10%'
       OR h_name ILIKE '%HCA 10%'
       OR db_slug ILIKE '%hca_10%'
    LIMIT 20;
""")

results = cur.fetchall()
print(f"\nFound {len(results)} results:\n")
for h_id, h_name, db_slug in results:
    print(f"h_id: '{h_id}'")
    print(f"h_name: '{h_name}'")
    print(f"db_slug: '{db_slug}'")
    print()

# Also check what Marrickville HCAs exist
print("\n" + "=" * 80)
print("All Marrickville HCAs:")
print("=" * 80)

cur.execute("""
    SELECT h_id, h_name, db_slug
    FROM heritage_conservation_areas
    WHERE lga_name ILIKE '%Inner West%'
      AND (h_name ILIKE '%Marrickville%' OR h_id LIKE 'HCA%')
    ORDER BY h_id
    LIMIT 30;
""")

results = cur.fetchall()
print(f"\nFound {len(results)} Marrickville HCAs:\n")
for h_id, h_name, db_slug in results:
    print(f"{h_id:15} | {h_name[:50]:50} | {db_slug}")

cur.close()
conn.close()
