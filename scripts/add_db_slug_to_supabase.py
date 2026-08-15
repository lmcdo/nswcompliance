#!/usr/bin/env python3
"""Add db_slug column to heritage_conservation_areas in Supabase"""
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

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 80)
    print("ADD DB_SLUG TO HERITAGE_CONSERVATION_AREAS - SUPABASE")
    print("=" * 80)
    print()

    # Step 1: Check if column exists
    print("Step 1: Checking if db_slug column exists...")
    print("-" * 80)

    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'heritage_conservation_areas'
          AND column_name = 'db_slug';
    """)

    exists = cur.fetchone() is not None

    if exists:
        print("  db_slug column already exists")
    else:
        print("  db_slug column does NOT exist - will create")

        # Add column
        cur.execute("""
            ALTER TABLE heritage_conservation_areas
            ADD COLUMN IF NOT EXISTS db_slug VARCHAR(150);
        """)
        conn.commit()
        print("  [OK] Added db_slug column")

    print()

    # Step 2: Count HCAs
    print("Step 2: Count HCAs")
    print("-" * 80)

    cur.execute("SELECT COUNT(*) FROM heritage_conservation_areas;")
    total_hcas = cur.fetchone()[0]
    print(f"  Total HCAs: {total_hcas}")

    cur.execute("SELECT COUNT(*) FROM heritage_conservation_areas WHERE db_slug IS NOT NULL;")
    with_slug = cur.fetchone()[0]
    print(f"  With db_slug: {with_slug}")
    print(f"  Need to populate: {total_hcas - with_slug}")
    print()

    # Step 3: Populate db_slug
    print("Step 3: Populating db_slug from h_name...")
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

            if updated <= 5:  # Show first 5 examples
                print(f"    {h_id:10s} -> {slug}")

    if updated > 5:
        print(f"    ... and {updated - 5} more")

    conn.commit()
    print(f"\n  [OK] Updated {updated} HCAs")
    print()

    # Step 4: Create index
    print("Step 4: Creating index on db_slug...")
    print("-" * 80)

    try:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_hca_db_slug
            ON heritage_conservation_areas(db_slug);
        """)
        conn.commit()
        print("  [OK] Index created")
    except Exception as e:
        print(f"  [INFO] Index may already exist: {e}")

    print()

    # Step 5: Verify C35
    print("Step 5: Verify C35 mapping")
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
    else:
        print("  [ERROR] C35 not found!")

    print()

    print("=" * 80)
    print("[COMPLETE] DB_SLUG COLUMN READY")
    print("=" * 80)
    print()
    print(f"  Total HCAs with db_slug: {total_hcas}")
    print(f"  C35 -> {result[2] if result else 'NOT FOUND'}")
    print()
    print("API can now resolve HCA codes!")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
