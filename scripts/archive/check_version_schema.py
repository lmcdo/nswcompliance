"""Check if version tracking schema exists in database"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_schema():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    # Check tables
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'provision_versions'
        )
    """)
    pv_exists = cur.fetchone()[0]
    print(f"provision_versions table exists: {pv_exists}")

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'provision_change_log'
        )
    """)
    pcl_exists = cur.fetchone()[0]
    print(f"provision_change_log table exists: {pcl_exists}")

    # Check new columns in regulatory_provisions
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name IN ('current_version_id', 'text_hash_current',
                              'version_count', 'is_current', 'first_seen_date',
                              'last_modified_date')
        ORDER BY column_name
    """)
    columns = [row[0] for row in cur.fetchall()]
    print(f"\nNew columns in regulatory_provisions: {columns}")

    if pv_exists:
        cur.execute("SELECT COUNT(*) FROM provision_versions")
        count = cur.fetchone()[0]
        print(f"\nprovision_versions row count: {count}")

    if pcl_exists:
        cur.execute("SELECT COUNT(*) FROM provision_change_log")
        count = cur.fetchone()[0]
        print(f"provision_change_log row count: {count}")

    # Check how many provisions have version tracking
    if columns:
        cur.execute("""
            SELECT
                COUNT(*) as total_provisions,
                COUNT(current_version_id) as provisions_with_version,
                COUNT(text_hash_current) as provisions_with_hash
            FROM regulatory_provisions
        """)
        result = cur.fetchone()
        print(f"\nTotal provisions: {result[0]}")
        print(f"Provisions with version tracking: {result[1]}")
        print(f"Provisions with text hash: {result[2]}")

    conn.close()

if __name__ == "__main__":
    check_schema()
