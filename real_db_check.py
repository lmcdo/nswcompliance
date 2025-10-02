#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def check_real_database():
    """Check the actual database with all populated tables"""

    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== ACTUAL DATABASE TABLES AND DATA ===')
            print()

            # Get all tables in public schema
            cur.execute("""
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname='public'
                ORDER BY tablename
            """)

            tables = cur.fetchall()
            print(f'Found {len(tables)} tables in public schema:')
            print()

            total_rows = 0
            populated_tables = []

            for table in tables:
                table_name = table['tablename']
                try:
                    cur.execute(f'SELECT COUNT(*) as count FROM "{table_name}"')
                    count = cur.fetchone()['count']
                    print(f'{table_name}: {count:,} rows')
                    total_rows += count

                    if count > 0:
                        populated_tables.append((table_name, count))

                except Exception as e:
                    print(f'{table_name}: Error - {e}')

            print()
            print(f'=== SUMMARY ===')
            print(f'Total tables: {len(tables)}')
            print(f'Populated tables: {len(populated_tables)}')
            print(f'Total rows across all tables: {total_rows:,}')
            print()

            # Show populated tables in detail
            if populated_tables:
                print('=== POPULATED TABLES DETAIL ===')
                for table_name, count in sorted(populated_tables, key=lambda x: x[1], reverse=True):
                    print(f'{table_name}: {count:,} rows')

                    # Get column info for populated tables
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                        LIMIT 10
                    """, (table_name,))

                    columns = cur.fetchall()
                    col_info = [f"{col['column_name']} ({col['data_type']})" for col in columns[:5]]
                    print(f'  Columns: {", ".join(col_info)}...')

                    # Get sample data
                    try:
                        cur.execute(f'SELECT * FROM "{table_name}" LIMIT 2')
                        sample = cur.fetchall()
                        if sample:
                            print(f'  Sample keys: {list(sample[0].keys())[:5]}...')
                    except:
                        pass
                    print()

    except Exception as e:
        print(f'Database error: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_real_database()