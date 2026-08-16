"""
Check dcp_precinct_boundaries table structure.
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

def check_structure():
    """Check table structure and sample data."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("DCP_PRECINCT_BOUNDARIES TABLE STRUCTURE")
    print("=" * 80)

    # Get column names
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'dcp_precinct_boundaries'
        ORDER BY ordinal_position;
    """)

    columns = cur.fetchall()
    print("\nColumns:")
    for col_name, data_type in columns:
        print(f"  - {col_name}: {data_type}")

    # Get total count
    cur.execute("SELECT COUNT(*) FROM dcp_precinct_boundaries;")
    total_count = cur.fetchone()[0]
    print(f"\nTotal rows: {total_count}")

    # Get all rows (limited columns)
    cur.execute("""
        SELECT id, precinct_id, precinct_name
        FROM dcp_precinct_boundaries
        ORDER BY precinct_id;
    """)

    rows = cur.fetchall()
    print(f"\n=== ALL PRECINCTS ({len(rows)} rows) ===\n")
    for id, precinct_id, name in rows:
        print(f"{precinct_id:20} | {name}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    check_structure()
