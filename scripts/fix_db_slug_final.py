#!/usr/bin/env python3
"""Fix db_slug column - handle long names"""
import psycopg2
import re

DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres.llzdrxywpziewrzudwhj',
    'password': 'eDDIYq8ottiaO9ll',
    'host': 'aws-1-ap-southeast-2.pooler.supabase.com',
    'port': 5432
}

def slugify(text, max_length=200):
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    slug = text.strip('_')

    # Truncate if too long
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('_')

    return slug

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("=" * 80)
print("FIX DB_SLUG - FINAL")
print("=" * 80)
print()

# Step 1: Increase column size
print("Step 1: Increasing column to VARCHAR(250)...")
cur.execute("""
    ALTER TABLE heritage_conservation_areas
    ALTER COLUMN db_slug TYPE VARCHAR(250);
""")
conn.commit()
print("  [OK] Column expanded")
print()

# Step 2: Populate with truncation
print("Step 2: Populating db_slug (max 200 chars)...")
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
        slug = slugify(h_name, max_length=200)

        cur.execute("""
            UPDATE heritage_conservation_areas
            SET db_slug = %s
            WHERE h_id = %s;
        """, (slug, h_id))

        updated += 1

        if updated <= 3:
            print(f"    {h_id:10s}: {slug[:60]}...")

if updated > 3:
    print(f"    ... and {updated - 3} more")

conn.commit()
print(f"\n  [OK] Updated {updated} HCAs")
print()

# Step 3: Verify C35
print("Step 3: Verify C35")
print("-" * 80)

cur.execute("""
    SELECT h_id, h_name, db_slug
    FROM heritage_conservation_areas
    WHERE h_id = 'C35';
""")

result = cur.fetchone()
if result:
    print(f"  [OK] C35 -> {result[2]}")
else:
    print("  [ERROR] C35 not found!")

print()

print("=" * 80)
print("[COMPLETE]")
print("=" * 80)
print()

cur.close()
conn.close()
