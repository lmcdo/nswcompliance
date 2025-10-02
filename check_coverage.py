import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check if table exists in public schema
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND (table_name LIKE '%provision%' OR table_name LIKE '%sepp%')
        """)
        tables = [t[0] for t in cur.fetchall()]
        print(f"Found tables: {tables}")

        # Try different table names
        provision_table = None
        for table in ['planning_provisions', 'provisions', 'sepp_provisions']:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table} LIMIT 1")
                provision_table = table
                print(f"Using table: {provision_table}")
                break
            except:
                pass

        if not provision_table:
            print("Could not find provisions table")
        else:
            # Check total provisions
            cur.execute(f'SELECT COUNT(*) FROM {provision_table}')
            total = cur.fetchone()[0]

            # Check provisions with full text
            cur.execute(f"SELECT COUNT(*) FROM {provision_table} WHERE full_provision_text IS NOT NULL AND full_provision_text != ''")
            with_text = cur.fetchone()[0]

            print(f'Overall: {with_text}/{total} ({with_text*100/total:.1f}%)')