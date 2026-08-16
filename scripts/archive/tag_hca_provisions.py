#!/usr/bin/env python3
"""
Tag Leichhardt heritage provisions with specific HCA slugs by parsing provision text.

Identifies HCA mentions in provision_text and updates v2_heritage_hca field.
"""
import psycopg2
import re
from collections import defaultdict

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

def normalize_hca_name(text):
    """Normalize HCA name for matching"""
    # Remove "Heritage Conservation Area" suffix
    text = re.sub(r'\s*Heritage Conservation Area\s*', ' ', text, flags=re.IGNORECASE)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text.strip()

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 80)
    print("HCA PROVISION TAGGING")
    print("=" * 80)
    print()

    # Step 1: Get all Leichhardt HCAs from heritage_conservation_areas
    print("Step 1: Loading Leichhardt HCAs...")
    cur.execute("""
        SELECT h_id, h_name, db_slug
        FROM heritage_conservation_areas
        WHERE lga_name = 'INNER WEST'
          AND h_id LIKE 'C%'
        ORDER BY LENGTH(h_name) DESC;  -- Match longer names first to avoid partial matches
    """)

    hcas = cur.fetchall()
    print(f"  Found {len(hcas)} Leichhardt HCAs")

    # Create lookup dict: normalized name -> db_slug
    hca_lookup = {}
    for h_id, h_name, db_slug in hcas:
        normalized = normalize_hca_name(h_name)
        hca_lookup[normalized.lower()] = {
            'h_id': h_id,
            'h_name': h_name,
            'db_slug': db_slug
        }

    print(f"  Sample HCAs:")
    for i, (h_id, h_name, db_slug) in enumerate(hcas[:5], 1):
        print(f"    {h_id}: {h_name[:50]} -> {db_slug}")
    print()

    # Step 2: Get all Leichhardt heritage provisions
    print("Step 2: Loading Leichhardt heritage provisions...")
    cur.execute("""
        SELECT id, provision_text, v2_heritage_hca, v2_dcp_part
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic ILIKE '%heritage%'
          AND v2_is_actionable = true
        ORDER BY id;
    """)

    provisions = cur.fetchall()
    print(f"  Found {len(provisions)} heritage provisions")
    print()

    # Step 3: Analyze and tag provisions
    print("Step 3: Analyzing provision text for HCA mentions...")
    print("-" * 80)

    matches = []
    no_match_count = 0
    already_tagged = 0

    for prov_id, prov_text, current_hca, dcp_part in provisions:
        if current_hca:
            already_tagged += 1
            continue

        if not prov_text:
            no_match_count += 1
            continue

        # Search for HCA names in provision text
        found_hca = None
        for normalized_name, hca_info in hca_lookup.items():
            # Try to find the HCA name in the provision text
            # Check both the full name and the name without "Heritage Conservation Area"
            full_name = hca_info['h_name']

            # Create regex pattern that matches the HCA name (case insensitive)
            pattern = re.escape(full_name)
            if re.search(pattern, prov_text, re.IGNORECASE):
                found_hca = hca_info
                break

            # Also try without the suffix
            if normalized_name and re.search(re.escape(normalized_name), prov_text, re.IGNORECASE):
                found_hca = hca_info
                break

        if found_hca:
            matches.append({
                'prov_id': prov_id,
                'hca_slug': found_hca['db_slug'],
                'hca_name': found_hca['h_name'],
                'h_id': found_hca['h_id'],
                'dcp_part': dcp_part
            })
        else:
            no_match_count += 1

    print(f"Results:")
    print(f"  Already tagged: {already_tagged}")
    print(f"  New matches found: {len(matches)}")
    print(f"  No HCA detected: {no_match_count}")
    print()

    # Show sample matches
    if matches:
        print("Sample matches:")
        for i, match in enumerate(matches[:10], 1):
            print(f"  {i}. Provision {match['prov_id']} ({match['dcp_part']})")
            print(f"     -> {match['h_id']}: {match['hca_name'][:50]}")
            print(f"     -> Tag with: {match['hca_slug']}")
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more")
        print()

        # Group by HCA
        by_hca = defaultdict(int)
        for match in matches:
            by_hca[match['hca_slug']] += 1

        print("Breakdown by HCA:")
        for hca_slug, count in sorted(by_hca.items(), key=lambda x: -x[1])[:10]:
            print(f"  {hca_slug:40s}: {count} provisions")
        print()

    # Step 4: Update database
    if len(matches) == 0:
        print("No provisions to update.")
        cur.close()
        conn.close()
        return

    response = input(f"Update {len(matches)} provisions with HCA tags? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        cur.close()
        conn.close()
        return

    print("\nStep 4: Updating database...")

    update_count = 0
    for match in matches:
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_heritage_hca = %s
            WHERE id = %s;
        """, (match['hca_slug'], match['prov_id']))
        update_count += 1

    conn.commit()
    print(f"  [OK] Updated {update_count} provisions")

    # Step 5: Verify specific HCAs
    print("\nStep 5: Verifying key HCAs...")

    test_hcas = ['parramatta_road', 'summer_hill', 'catherine_street']
    for hca_slug in test_hcas:
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE v2_heritage_hca = %s;
        """, (hca_slug,))
        count = cur.fetchone()[0]
        print(f"  {hca_slug:30s}: {count} provisions")

    # Step 6: Final stats
    print("\nStep 6: Final statistics...")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE v2_heritage_hca IS NOT NULL) as tagged,
            COUNT(*) FILTER (WHERE v2_heritage_hca IS NULL) as untagged,
            COUNT(*) as total
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic ILIKE '%heritage%'
          AND v2_is_actionable = true;
    """)

    row = cur.fetchone()
    print(f"  Total provisions: {row[2]}")
    print(f"  Tagged with HCA: {row[0]} ({100*row[0]//row[2]}%)")
    print(f"  General (NULL): {row[1]} ({100*row[1]//row[2]}%)")

    print("\n" + "=" * 80)
    print("[COMPLETE] HCA TAGGING COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Test API: /api/provisions/for-property?hca=C35&heritage=true")
    print("  2. Verify Parramatta Road HCA provisions load")
    print("  3. Check UI shows HCA-specific provisions")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
