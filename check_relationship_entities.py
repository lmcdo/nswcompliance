#!/usr/bin/env python3
"""
Check relationship entities in the database
COMPLIANT with PRP-A1 Database Safety Requirements
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# MANDATORY: Use db_safety_wrapper per CLAUDE.md
from db_safety_wrapper import get_safe_connection

def check_relationship_entities():
    """
    Check all relationship/junction tables and foreign key relationships
    SAFETY: Read-only operations with 30-second timeout enforced
    """

    # MANDATORY: Use safe connection context manager
    with get_safe_connection() as conn:
        with conn.cursor() as cur:

            # Get all tables (read-only, WHERE clause not applicable)
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [t[0] for t in cur.fetchall()]

            print("=== ALL TABLES ===")
            for table in tables:
                print(f"  - {table}")

            # Find relationship/junction tables
            print("\n=== RELATIONSHIP/JUNCTION TABLES ===")
            relationship_keywords = ['relationship', 'junction', 'link', 'map', 'cross', 'ref']

            for table in tables:
                if any(kw in table.lower() for kw in relationship_keywords):
                    print(f"\n{table}:")

                    # Get columns
                    cur.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table,))
                    columns = cur.fetchall()

                    for col, dtype in columns:
                        print(f"  - {col}: {dtype}")

                    # Get count (safe - no WHERE needed for COUNT)
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    print(f"  Count: {count}")

            # Get foreign key relationships
            print("\n=== FOREIGN KEY RELATIONSHIPS ===")
            cur.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                ORDER BY tc.table_name
            """)
            fks = cur.fetchall()

            if fks:
                for table, col, foreign_table, foreign_col in fks:
                    print(f"  {table}.{col} -> {foreign_table}.{foreign_col}")
            else:
                print("  No foreign key relationships found")

            # Check for potential relationship patterns (many-to-many)
            print("\n=== POTENTIAL MANY-TO-MANY RELATIONSHIPS ===")
            for table in tables:
                # Get columns
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND column_name LIKE '%%_id'
                """, (table,))
                id_columns = [c[0] for c in cur.fetchall()]

                # If table has 2+ foreign key columns, it's likely a junction table
                if len(id_columns) >= 2:
                    print(f"  {table}: {', '.join(id_columns)}")

if __name__ == '__main__':
    try:
        print("🛡️ DATABASE SAFETY: Using db_safety_wrapper (30s timeout)\n")
        check_relationship_entities()
        print("\n✅ Query completed safely")
    except Exception as e:
        print(f"\n❌ Database safety error: {str(e)}", file=sys.stderr)
        sys.exit(1)