"""
Examine precinct provision patterns to understand document_id structure
for each council, needed for v2_precinct_id enrichment.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv('frontend-nextjs/.env.local')

def get_db_connection():
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv('PGHOST'),
        database=os.getenv('PGDATABASE'),
        user=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        port=os.getenv('PGPORT')
    )

def examine_patterns():
    """Examine precinct provision patterns for all three councils."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("EXAMINING PRECINCT PROVISION PATTERNS")
    print("=" * 80)

    # Get counts by council
    print("\n=== PRECINCT PROVISION COUNTS ===\n")
    for council in ['Marrickville', 'Leichhardt', 'Ashfield']:
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_dcp_layer = 'precinct'
              AND v2_is_actionable = true;
        """, (f'%{council}%',))
        count = cur.fetchone()[0]
        print(f"{council}: {count} provisions")

    # Get Marrickville samples and unique documents
    print("\n" + "=" * 80)
    print("MARRICKVILLE PRECINCT PATTERNS")
    print("=" * 80)

    cur.execute("""
        SELECT DISTINCT document_id, v2_dcp_part, v2_precinct_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY document_id
        LIMIT 20;
    """)

    marrickville_samples = cur.fetchall()
    print(f"\nFound {len(marrickville_samples)} unique document patterns (showing first 20):\n")
    for doc_id, part, precinct_id in marrickville_samples:
        print(f"Document: {doc_id}")
        print(f"  Part: {part}, Current v2_precinct_id: {precinct_id}")
        print()

    # Get Leichhardt samples
    print("=" * 80)
    print("LEICHHARDT PRECINCT PATTERNS")
    print("=" * 80)

    cur.execute("""
        SELECT DISTINCT document_id, v2_dcp_part, v2_precinct_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY document_id
        LIMIT 20;
    """)

    leichhardt_samples = cur.fetchall()
    print(f"\nFound {len(leichhardt_samples)} unique document patterns (showing first 20):\n")
    for doc_id, part, precinct_id in leichhardt_samples:
        print(f"Document: {doc_id}")
        print(f"  Part: {part}, Current v2_precinct_id: {precinct_id}")
        print()

    # Get Ashfield samples
    print("=" * 80)
    print("ASHFIELD PRECINCT PATTERNS")
    print("=" * 80)

    cur.execute("""
        SELECT DISTINCT document_id, v2_dcp_part, v2_precinct_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY document_id
        LIMIT 20;
    """)

    ashfield_samples = cur.fetchall()
    print(f"\nFound {len(ashfield_samples)} unique document patterns (showing first 20):\n")
    for doc_id, part, precinct_id in ashfield_samples:
        print(f"Document: {doc_id}")
        print(f"  Part: {part}, Current v2_precinct_id: {precinct_id}")
        print()

    # Get all unique Marrickville documents (to understand full pattern)
    cur.execute("""
        SELECT document_id, COUNT(*) as provision_count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        GROUP BY document_id
        ORDER BY document_id;
    """)

    marrickville_docs = cur.fetchall()
    print("=" * 80)
    print(f"ALL MARRICKVILLE PRECINCT DOCUMENTS ({len(marrickville_docs)} total)")
    print("=" * 80)
    for doc_id, count in marrickville_docs:
        print(f"{doc_id}: {count} provisions")

    cur.close()
    conn.close()

if __name__ == '__main__':
    examine_patterns()
