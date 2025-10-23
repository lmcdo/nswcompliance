"""
Fix provision ID mapping in dcp_precinct_requirements

The issue: Week 2 stored IDs from dcp_precinct_provisions table (e.g., 292-296),
but source traceability API queries regulatory_provisions table (e.g., 75424-75428).

Solution: Map provision IDs from dcp_precinct_provisions -> regulatory_provisions
using document_id and provision_text as matching criteria.
"""

from db_safety_wrapper import get_safe_connection
import json

def create_id_mapping(conn):
    """Create mapping dict from dcp_precinct_provisions IDs to regulatory_provisions IDs"""
    cur = conn.cursor()

    print("Creating ID mapping between tables...")

    cur.execute("""
        SELECT
            dpp.id as old_id,
            rp.id as new_id,
            dpp.document_id
        FROM dcp_precinct_provisions dpp
        INNER JOIN regulatory_provisions rp
            ON dpp.document_id = rp.document_id
            AND dpp.provision_text = rp.provision_text
        ORDER BY dpp.id
    """)

    rows = cur.fetchall()

    mapping = {}
    for old_id, new_id, doc_id in rows:
        mapping[old_id] = new_id

    print(f"  Created mapping for {len(mapping)} provisions")
    print(f"  Sample mappings:")
    for old_id, new_id in list(mapping.items())[:5]:
        print(f"    {old_id} -> {new_id}")

    return mapping

def fix_requirements_ids(conn, mapping):
    """Update source_provision_ids in dcp_precinct_requirements"""
    cur = conn.cursor()

    print("\nFixing provision IDs in dcp_precinct_requirements...")

    # Get all requirements
    cur.execute("""
        SELECT id, source_provision_ids, precinct_name
        FROM dcp_precinct_requirements
        ORDER BY id
    """)

    requirements = cur.fetchall()
    print(f"  Found {len(requirements)} requirements to fix")

    updated_count = 0
    error_count = 0

    for req_id, old_ids, precinct_name in requirements:
        if not old_ids:
            continue

        # Map old IDs to new IDs
        new_ids = []
        unmapped = []

        for old_id in old_ids:
            if old_id in mapping:
                new_ids.append(mapping[old_id])
            else:
                unmapped.append(old_id)

        if unmapped:
            print(f"    WARNING: Req {req_id} ({precinct_name}): Could not map IDs {unmapped}")
            error_count += 1

        if new_ids:
            # Update with new IDs
            cur.execute("""
                UPDATE dcp_precinct_requirements
                SET source_provision_ids = %s
                WHERE id = %s
            """, (new_ids, req_id))

            updated_count += 1

            if updated_count % 50 == 0:
                print(f"    Updated {updated_count} requirements...")

    conn.commit()

    print(f"\n  Updated: {updated_count} requirements")
    print(f"  Errors: {error_count} requirements with unmapped IDs")

    return updated_count, error_count

def verify_fix(conn):
    """Verify that the fix worked"""
    cur = conn.cursor()

    print("\nVerifying fix...")

    # Get a sample requirement
    cur.execute("""
        SELECT id, precinct_name, category, source_provision_ids
        FROM dcp_precinct_requirements
        WHERE precinct_name = 'Abergeldie Estate'
        LIMIT 1
    """)

    row = cur.fetchone()
    if not row:
        print("  ERROR: No Abergeldie requirements found")
        return False

    req_id, precinct_name, category, source_ids = row

    print(f"\n  Sample: Req {req_id} ({precinct_name}, {category})")
    print(f"    source_provision_ids: {source_ids}")

    # Check if these IDs exist in regulatory_provisions
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE id = ANY(%s)
    """, (source_ids,))

    count = cur.fetchone()[0]

    print(f"    Found in regulatory_provisions: {count}/{len(source_ids)}")

    if count == len(source_ids):
        print("\n  SUCCESS: All provision IDs now exist in regulatory_provisions")
        return True
    else:
        print(f"\n  WARNING: Only {count}/{len(source_ids)} IDs found")
        return False

def main():
    print("=" * 80)
    print("FIX PROVISION ID MAPPING")
    print("=" * 80)

    conn = get_safe_connection()

    try:
        # Create mapping
        mapping = create_id_mapping(conn)

        if not mapping:
            print("\nERROR: Could not create ID mapping")
            return

        # Fix IDs
        updated, errors = fix_requirements_ids(conn, mapping)

        # Verify
        success = verify_fix(conn)

        if success:
            print("\n" + "=" * 80)
            print("FIX COMPLETE")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("FIX COMPLETED WITH WARNINGS")
            print("=" * 80)

    finally:
        conn.close()

if __name__ == '__main__':
    main()
