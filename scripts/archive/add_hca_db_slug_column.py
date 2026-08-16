#!/usr/bin/env python3
"""
Add db_slug column to heritage_conservation_areas table and populate it.

This enables HCA filtering: C35 (h_id) -> parramatta_road (db_slug) -> matches v2_heritage_hca
"""
import psycopg2
import re

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

def slugify_hca_name(h_name):
    """Convert HCA name to slug format"""
    # Remove "Heritage Conservation Area" suffix
    slug = re.sub(r'\s*Heritage Conservation Area\s*$', '', h_name, flags=re.IGNORECASE)

    # Remove "Precinct" if present
    slug = re.sub(r'\s*Precinct\s*', ' ', slug, flags=re.IGNORECASE)

    # Remove extra whitespace
    slug = slug.strip()

    # Convert to lowercase and replace spaces/special chars with underscores
    slug = slug.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)

    # Remove leading/trailing underscores
    slug = slug.strip('_')

    # For items (not conservation areas), prefix with item_
    if not slug:
        slug = 'unknown'

    return slug

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 80)
    print("HCA DB_SLUG MIGRATION")
    print("=" * 80)
    print()

    # Step 1: Check if column already exists
    print("Step 1: Checking if db_slug column exists...")
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'heritage_conservation_areas'
          AND column_name = 'db_slug';
    """)

    if cur.fetchone():
        print("  [OK] db_slug column already exists")
    else:
        print("  Adding db_slug column...")
        cur.execute("""
            ALTER TABLE heritage_conservation_areas
            ADD COLUMN db_slug VARCHAR(150);
        """)
        conn.commit()
        print("  [OK] Column added")

    # Step 2: Get all HCAs and generate slugs
    print("\nStep 2: Generating slugs for all HCAs...")
    cur.execute("""
        SELECT id, h_id, h_name, lay_class
        FROM heritage_conservation_areas
        ORDER BY h_id;
    """)

    hcas = cur.fetchall()
    print(f"  Found {len(hcas)} HCAs")

    # Step 3: Generate and display slug mappings
    print("\nStep 3: Preview slug mappings...")
    print("-" * 80)

    mappings = []
    for row in hcas[:10]:  # Show first 10 as preview
        hca_id, h_id, h_name, lay_class = row
        slug = slugify_hca_name(h_name)
        mappings.append((hca_id, h_id, h_name, slug))
        print(f"  {h_id} | {h_name[:40]:40s} -> {slug}")

    print(f"  ... and {len(hcas) - 10} more")
    print()

    # Step 4: Update all records
    response = input(f"Update {len(hcas)} records with slugs? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        cur.close()
        conn.close()
        return

    print("\nStep 4: Updating db_slug values...")

    update_count = 0
    for row in hcas:
        hca_id, h_id, h_name, lay_class = row
        slug = slugify_hca_name(h_name)

        cur.execute("""
            UPDATE heritage_conservation_areas
            SET db_slug = %s
            WHERE id = %s;
        """, (slug, hca_id))

        update_count += 1

    conn.commit()
    print(f"  [OK] Updated {update_count} records")

    # Step 5: Verify Parramatta Road HCA specifically
    print("\nStep 5: Verifying Parramatta Road HCA (C35)...")
    cur.execute("""
        SELECT h_id, h_name, db_slug
        FROM heritage_conservation_areas
        WHERE h_id = 'C35';
    """)

    result = cur.fetchone()
    if result:
        print(f"  H_ID: {result[0]}")
        print(f"  Name: {result[1]}")
        print(f"  Slug: {result[2]}")

        # Check if this slug exists in provisions
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE v2_heritage_hca = %s;
        """, (result[2],))

        prov_count = cur.fetchone()[0]
        print(f"  Provisions with this slug: {prov_count}")

        if prov_count == 0:
            print(f"  [WARNING]  WARNING: No provisions found with v2_heritage_hca = '{result[2]}'")
            print(f"      This HCA may need provision extraction/tagging")
    else:
        print("  [ERROR] C35 not found!")

    # Step 6: Show stats
    print("\nStep 6: Migration statistics...")
    cur.execute("""
        SELECT COUNT(*) FROM heritage_conservation_areas WHERE db_slug IS NOT NULL;
    """)
    total_with_slug = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM heritage_conservation_areas;
    """)
    total = cur.fetchone()[0]

    print(f"  Total HCAs: {total}")
    print(f"  With db_slug: {total_with_slug}")
    print(f"  Coverage: {100*total_with_slug//total}%")

    # Step 7: Create index for performance
    print("\nStep 7: Creating index on db_slug...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_hca_db_slug
        ON heritage_conservation_areas(db_slug);
    """)
    conn.commit()
    print("  [OK] Index created")

    print("\n" + "=" * 80)
    print("[COMPLETE] MIGRATION COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Test API: /api/provisions/for-property?hca=C35&heritage=true")
    print("  2. Verify HCA-specific provisions load correctly")
    print("  3. Check UI displays Parramatta Road HCA provisions")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
