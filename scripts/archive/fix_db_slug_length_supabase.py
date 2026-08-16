#!/usr/bin/env python3
"""Fix db_slug column length in Supabase"""
import psycopg2
import re

DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres.llzdrxywpziewrzudwhj',
    'password': 'eDDIYq8ottiaO9ll',
    'host': 'aws-1-ap-southeast-2.pooler.supabase.com',
    'port': 5432
}

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("=" * 80)
print("FIX DB_SLUG COLUMN LENGTH - SUPABASE")
print("=" * 80)
print()

# Step 1: Alter column length
print("Step 1: Increasing db_slug column length...")
print("-" * 80)

cur.execute("""
    ALTER TABLE heritage_conservation_areas
    ALTER COLUMN db_slug TYPE VARCHAR(150);
""")
conn.commit()
print("  [OK] Changed db_slug from VARCHAR(50) to VARCHAR(150)")
print()

# Step 2: Populate all NULL db_slugs
print("Step 2: Populating db_slug for all HCAs...")
print("-" * 80)

cur.execute("""
    SELECT h_id, h_name
    FROM heritage_conservation_areas
    WHERE db_slug IS NULL OR db_slug = '';
""")

to_update = cur.fetchall()
print(f"  Processing {len(to_update)} HCAs...")

updated = 0
for h_id, h_name in to_update:
    if h_name:
        slug = slugify(h_name)

        cur.execute("""
            UPDATE heritage_conservation_areas
            SET db_slug = %s
            WHERE h_id = %s;
        """, (slug, h_id))

        updated += 1

        if updated <= 5:
            print(f"    {h_id:10s}: {h_name[:40]:40s} -> {slug}")

if updated > 5:
    print(f"    ... and {updated - 5} more")

conn.commit()
print(f"\n  [OK] Updated {updated} HCAs")
print()

# Step 3: Verify C35
print("Step 3: Verify C35 mapping")
print("-" * 80)

cur.execute("""
    SELECT h_id, h_name, db_slug
    FROM heritage_conservation_areas
    WHERE h_id = 'C35';
""")

result = cur.fetchone()
if result:
    print(f"  h_id: {result[0]}")
    print(f"  h_name: {result[1]}")
    print(f"  db_slug: {result[2]}")
    print()
    print(f"  [OK] C35 -> {result[2]}")
else:
    print("  [ERROR] C35 not found!")

print()

# Step 4: Summary
print("Step 4: Summary")
print("-" * 80)

cur.execute("SELECT COUNT(*) FROM heritage_conservation_areas WHERE db_slug IS NOT NULL;")
with_slug = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM heritage_conservation_areas;")
total = cur.fetchone()[0]

print(f"  Total HCAs: {total}")
print(f"  With db_slug: {with_slug}")
print(f"  Coverage: {with_slug/total*100:.1f}%")
print()

print("=" * 80)
print("[COMPLETE] DB_SLUG READY IN SUPABASE")
print("=" * 80)
print()
print("API can now resolve HCA codes (e.g., C35 -> parramatta_road)")
print()

cur.close()
conn.close()
