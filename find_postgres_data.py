#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def find_postgres_databases():
    """Find all PostgreSQL databases and their data"""

    try:
        # Connect to default postgres database to list all databases
        conn = psycopg2.connect(
            host='localhost',
            user='postgres',
            password='postgres',
            port='5432',
            database='postgres'
        )

        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
            databases = [row[0] for row in cur.fetchall()]

        conn.close()

        print('=== ALL POSTGRESQL DATABASES ===')
        for db in databases:
            print(f'  - {db}')
        print()

        # Check each database for data
        for db_name in databases:
            try:
                print(f'=== {db_name.upper()} DATABASE ===')

                conn = psycopg2.connect(
                    host='localhost',
                    database=db_name,
                    user='postgres',
                    password='postgres',
                    port='5432'
                )

                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get all schemas
                    cur.execute("""
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_toast_temp_1')
                        ORDER BY schema_name
                    """)
                    schemas = [row['schema_name'] for row in cur.fetchall()]
                    print(f'Schemas: {schemas}')

                    # Get all tables with row counts
                    total_rows = 0
                    populated_tables = []

                    for schema in schemas:
                        cur.execute(f"""
                            SELECT tablename
                            FROM pg_tables
                            WHERE schemaname = '{schema}'
                            ORDER BY tablename
                        """)
                        tables = [row['tablename'] for row in cur.fetchall()]

                        print(f'\nSchema "{schema}" has {len(tables)} tables')

                        for table in tables:
                            try:
                                cur.execute(f'SELECT COUNT(*) as count FROM "{schema}"."{table}"')
                                count = cur.fetchone()['count']
                                total_rows += count

                                if count > 0:
                                    populated_tables.append((schema, table, count))

                            except Exception as e:
                                print(f'  Error counting {schema}.{table}: {e}')

                    print(f'\nTotal rows across all tables: {total_rows:,}')
                    print(f'Populated tables: {len(populated_tables)}')

                    if populated_tables:
                        print('\nPopulated tables:')
                        for schema, table, count in sorted(populated_tables, key=lambda x: x[2], reverse=True):
                            print(f'  {schema}.{table}: {count:,} rows')

                            # Show sample data for largest tables
                            if count > 1000:
                                try:
                                    cur.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 1')
                                    sample = cur.fetchone()
                                    if sample:
                                        keys = list(sample.keys())[:5]
                                        print(f'    Columns: {", ".join(keys)}...')
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
    find_postgres_databases()