import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check what tables exist
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE '%sepp%'
            OR table_name LIKE '%provision%'
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        print("SEPP-related tables:")
        for table in tables:
            print(f"  - {table[0]}")

            # Get count for each table
            cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cur.fetchone()[0]
            print(f"    Count: {count}")