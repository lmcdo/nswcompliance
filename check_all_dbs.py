#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def check_all_databases():
    """Check all databases for populated tables"""

    try:
        # First, get list of all databases
        conn = psycopg2.connect(
            host='localhost',
            user='postgres',
            password='postgres',
            port='5432',
            database='postgres'
        )

        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
            databases = [row[0] for row in cur.fetchall()]

        conn.close()

        print('=== ALL POSTGRESQL DATABASES ===')
        for db in databases:
            print(f'  - {db}')
        print()

        # Check each database for tables and data
        for db_name in databases:
            if db_name in ['postgres']:
                continue

            try:
                print(f'=== DATABASE: {db_name} ===')

                conn = psycopg2.connect(
                    host='localhost',
                    database=db_name,
                    user='postgres',
                    password='postgres',
                    port='5432'
                )

                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get all tables
                    cur.execute("""
                        SELECT tablename
                        FROM pg_tables
                        WHERE schemaname='public'
                        ORDER BY tablename
                    """)

                    tables = [row['tablename'] for row in cur.fetchall()]
                    print(f'Tables found: {len(tables)}')

                    if tables:
                        total_rows = 0
                        populated_tables = []

                        for table in tables:
                            try:
                                cur.execute(f'SELECT COUNT(*) as count FROM "{table}"')
                                count = cur.fetchone()['count']
                                total_rows += count

                                if count > 0:
                                    populated_tables.append((table, count))

                            except Exception as e:
                                print(f'  {table}: Error - {e}')

                        print(f'Total rows: {total_rows:,}')
                        print(f'Populated tables: {len(populated_tables)}')

                        if populated_tables:
                            print('Populated tables:')
                            for table_name, count in sorted(populated_tables, key=lambda x: x[1], reverse=True):
                                print(f'  {table_name}: {count:,} rows')

                                # Show sample data for large tables
                                if count > 1000:
                                    try:
                                        cur.execute(f'SELECT * FROM "{table_name}" LIMIT 1')
                                        sample = cur.fetchone()
                                        if sample:
                                            keys = list(sample.keys())[:5]
                                            print(f'    Sample columns: {", ".join(keys)}...')
                                    except:
                                        pass

                conn.close()
                print()

            except Exception as e:
                print(f'Error accessing {db_name}: {e}')
                print()

    except Exception as e:
        print(f'Error connecting to PostgreSQL: {e}')

if __name__ == "__main__":
    check_all_databases()