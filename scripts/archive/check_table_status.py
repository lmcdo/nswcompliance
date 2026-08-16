#!/usr/bin/env python3
"""Check regulatory_provisions table status"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 60)
print("REGULATORY_PROVISIONS TABLE STATUS CHECK")
print("=" * 60)

# Check backend
cur.execute('SELECT pg_backend_pid()')
backend_pid = cur.fetchone()[0]
print(f"\nBackend PID: {backend_pid}")

# Check table row count
cur.execute('SELECT COUNT(*) FROM regulatory_provisions')
count = cur.fetchone()[0]
print(f"Row count: {count}")

if count == 0:
    print("\n[WARN] Table is empty!")

    # Check if table was truncated recently
    cur.execute("""
        SELECT n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
        FROM pg_stat_user_tables
        WHERE tablename = 'regulatory_provisions'
    """)
    result = cur.fetchone()
    print(f"\nTable statistics:")
    print(f"  - Inserts: {result[0]}")
    print(f"  - Updates: {result[1]}")
    print(f"  - Deletes: {result[2]}")
    print(f"  - Live tuples: {result[3]}")
    print(f"  - Dead tuples: {result[4]}")

    # Check other related tables
    print("\nChecking related tables:")
    for table in ['provision_versions', 'provision_change_log', 'documents', 'dcp_general_requirements']:
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            tbl_count = cur.fetchone()[0]
            print(f"  - {table}: {tbl_count} rows")
        except Exception as e:
            print(f"  - {table}: Error - {e}")

# Check for foreign key constraints
cur.execute("""
    SELECT conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'regulatory_provisions'::regclass
    AND contype = 'f'
""")
fks = cur.fetchall()
print(f"\nForeign key constraints: {len(fks)}")
for fk in fks:
    print(f"  - {fk[0]}: {fk[2]}")

# Check if there are any locks
cur.execute("""
    SELECT locktype, relation::regclass, mode, granted
    FROM pg_locks
    WHERE relation = 'regulatory_provisions'::regclass
""")
locks = cur.fetchall()
if locks:
    print(f"\nActive locks: {len(locks)}")
    for lock in locks:
        print(f"  - {lock}")
else:
    print("\nNo active locks")

conn.close()
print("\n" + "=" * 60)
