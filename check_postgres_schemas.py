#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def check_postgres_schemas():
    """Check all schemas in the PostgreSQL nsw_planning database"""

    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== POSTGRESQL NSW_PLANNING DATABASE - COMPLETE ANALYSIS ===')
            print()

            # Check all schemas and their tables
            schemas = ['public', 'authoritative', 'versions']

            for schema in schemas:
                print(f'=== SCHEMA: {schema.upper()} ===')

                # Get all tables in this schema
                cur.execute(f"""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = '{schema}'
                    ORDER BY tablename
                """)
                tables = [row['tablename'] for row in cur.fetchall()]

                print(f'Tables: {len(tables)}')

                total_rows = 0
                for table in tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) as count FROM "{schema}"."{table}"')
                        count = cur.fetchone()['count']
                        total_rows += count

                        print(f'  {table}: {count:,} rows')

                        # Show columns for populated tables
                        if count > 0:
                            cur.execute(f"""
                                SELECT column_name, data_type
                                FROM information_schema.columns
                                WHERE table_schema = '{schema}' AND table_name = '{table}'
                                ORDER BY ordinal_position
                                LIMIT 8
                            """)
                            columns = cur.fetchall()
                            col_names = [f"{col['column_name']} ({col['data_type']})" for col in columns]
                            print(f'    Columns: {", ".join(col_names)}')

                            # Show sample data
                            if count > 10:
                                cur.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 2')
                                samples = cur.fetchall()
                                if samples:
                                    print(f'    Sample data available: {len(list(samples[0].keys()))} fields')

                    except Exception as e:
                        print(f'  {table}: Error - {e}')

                print(f'Schema total: {total_rows:,} rows')
                print()

            # Check if this looks like the migrated SQLite data
            print('=== MIGRATION ANALYSIS ===')

            # Check for key tables that should exist from SQLite
            expected_tables = [
                'regulatory_provisions',
                'development_controls',
                'kg_entities',
                'kg_relationships',
                'visual_elements_real',
                'contextual_guidance_real',
                'quantitative_standards'
            ]

            print('Expected tables from SQLite migration:')
            for table in expected_tables:
                try:
                    cur.execute(f'SELECT COUNT(*) as count FROM public."{table}"')
                    count = cur.fetchone()['count']
                    status = "✅ FOUND" if count > 0 else "❌ EMPTY"
                    print(f'  {table}: {count:,} rows {status}')
                except:
                    print(f'  {table}: ❌ NOT FOUND')

            print()

            # Check if data is distributed across schemas
            print('=== SCHEMA DISTRIBUTION ===')
            for schema in schemas:
                cur.execute(f"""
                    SELECT SUM(
                        (xpath('/row/c/text()', query_to_xml(
                            format('SELECT count(*) AS c FROM %I.%I', schemaname, tablename),
                            false, true, ''
                        )))[1]::text::int
                    ) as total_rows
                    FROM pg_tables
                    WHERE schemaname = '{schema}'
                    GROUP BY schemaname
                """)
                try:
                    result = cur.fetchone()
                    total = result['total_rows'] if result else 0
                    print(f'{schema}: {total:,} total rows')
                except:
                    print(f'{schema}: Cannot calculate total')

        conn.close()

    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    check_postgres_schemas()