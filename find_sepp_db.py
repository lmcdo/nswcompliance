#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def find_databases_with_most_tables():
    databases_to_check = [
        'nsw_planning',
        'compliance_engine',
        'postgres',
        'planning_data',
        'sepp_data',
        'nsw_compliance'
    ]

    passwords_to_try = ['postgres', 'Gu3ssth!s', 'password', 'admin']

    results = []

    for db_name in databases_to_check:
        for password in passwords_to_try:
            try:
                conn = psycopg2.connect(
                    host='localhost',
                    database=db_name,
                    user='postgres',
                    password=password,
                    port='5432'
                )

                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT COUNT(*) as table_count
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                    """)

                    table_count = cur.fetchone()['table_count']

                    # Check for SEPP-related tables
                    cur.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND (table_name ILIKE '%sepp%' OR table_name ILIKE '%provision%')
                        ORDER BY table_name
                    """)

                    sepp_tables = cur.fetchall()

                    results.append({
                        'database': db_name,
                        'password': password,
                        'table_count': table_count,
                        'sepp_tables': [t['table_name'] for t in sepp_tables]
                    })

                    print(f"✅ {db_name} (password: {password}): {table_count} tables")
                    if sepp_tables:
                        print(f"   SEPP-related tables: {[t['table_name'] for t in sepp_tables]}")
                    print()

                conn.close()
                break  # Found working credentials, move to next database

            except Exception as e:
                continue  # Try next password

    # Show summary
    print("=== SUMMARY ===")
    results.sort(key=lambda x: x['table_count'], reverse=True)
    for result in results:
        print(f"{result['database']}: {result['table_count']} tables")
        if result['sepp_tables']:
            print(f"  SEPP tables: {result['sepp_tables']}")

if __name__ == "__main__":
    find_databases_with_most_tables()