#!/usr/bin/env python3
"""Check all tables in the database for DCP full text"""

from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
cur = conn.cursor()

# Get all tables
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

tables = [row[0] for row in cur.fetchall()]

print("ALL TABLES IN DATABASE:")
print("="*80)
for table in tables:
    print(f"  {table}")

print("\n\nCHECKING TABLES FOR DCP/DOCUMENT TEXT:")
print("="*80)

# Check each table for text columns
for table in tables:
    if 'doc' in table.lower() or 'text' in table.lower() or 'provision' in table.lower() or 'rag' in table.lower():
        cur.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND column_name LIKE '%text%'
        """)

        text_cols = cur.fetchall()
        if text_cols:
            print(f"\n{table}:")
            for col, dtype in text_cols:
                print(f"  - {col} ({dtype})")

            # Check row count
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  Total rows: {count:,}")

cur.close()
conn.close()
