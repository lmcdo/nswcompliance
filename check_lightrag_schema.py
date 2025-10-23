"""
Check if LightRAG categorization database schema exists
"""
import os
from dotenv import load_dotenv
from db_safety_wrapper import get_safe_connection

load_dotenv()

with get_safe_connection(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    port=int(os.getenv('PGPORT', 5432))
) as safe_conn:
    cur = safe_conn.cursor()

    print("=" * 80)
    print("LIGHTRAG DATABASE SCHEMA CHECK")
    print("=" * 80)

    # Check for required tables
    required_tables = [
        'dcp_base_requirements',
        'dcp_precinct_requirements',
        'categorization_validation'
    ]

    print("\n1. CHECKING FOR REQUIRED TABLES:")
    existing_tables = []
    missing_tables = []

    for table in required_tables:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table,))
        exists = cur.fetchone()[0]

        if exists:
            existing_tables.append(table)
            print(f"  [EXISTS] {table}")
        else:
            missing_tables.append(table)
            print(f"  [MISSING] {table}")

    # Check existing table schemas if any exist
    if existing_tables:
        print("\n2. EXISTING TABLE SCHEMAS:")
        for table in existing_tables:
            print(f"\n  Table: {table}")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = cur.fetchall()
            for col_name, col_type, nullable in columns:
                null_str = "NULL" if nullable == 'YES' else "NOT NULL"
                print(f"    {col_name}: {col_type} {null_str}")

            # Check row count
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"    Row count: {count}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Existing tables: {len(existing_tables)}/{len(required_tables)}")
    print(f"Missing tables: {len(missing_tables)}/{len(required_tables)}")

    if missing_tables:
        print("\nMISSING TABLES:")
        for table in missing_tables:
            print(f"  - {table}")
        print("\nNEXT STEP: Create database schema for LightRAG categorization")
    else:
        print("\nSTATUS: All required tables exist")
        print("NEXT STEP: Verify schema matches requirements and start processing")

    print("=" * 80)
