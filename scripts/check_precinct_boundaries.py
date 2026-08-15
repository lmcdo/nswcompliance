"""
Check precinct boundaries table to understand expected precinct_id format.
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

def check_boundaries():
    """Check precinct boundaries for each council."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("PRECINCT BOUNDARIES TABLE")
    print("=" * 80)

    # Get all precincts grouped by council
    for council in ['Marrickville', 'Leichhardt', 'Ashfield']:
        cur.execute("""
            SELECT precinct_id, precinct_name, council
            FROM dcp_precinct_boundaries
            WHERE council ILIKE %s
            ORDER BY precinct_id;
        """, (f'%{council}%',))

        precincts = cur.fetchall()
        print(f"\n=== {council.upper()} PRECINCTS ({len(precincts)} total) ===\n")
        for precinct_id, name, council_name in precincts:
            print(f"{precinct_id:20} | {name}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    check_boundaries()
