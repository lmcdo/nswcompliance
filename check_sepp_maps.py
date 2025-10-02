#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def check_sepp_maps():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== Checking sepp_lep_overrides table ===')
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'sepp_lep_overrides'
                ORDER BY ordinal_position
            """)

            columns = cur.fetchall()
            for col in columns:
                print(f'Column: {col["column_name"]} ({col["data_type"]})')

            print('\n=== Sample SEPP Override Data ===')
            cur.execute("""
                SELECT *
                FROM sepp_lep_overrides
                LIMIT 5
            """)

            sepp_data = cur.fetchall()
            for row in sepp_data:
                print(f'Row: {dict(row)}')
                print()

            print('\n=== Search All Tables for SEPP Map Data ===')

            # Check each table for SEPP/map content
            tables_to_check = [
                'regulatory_provisions',
                'regulatory_provisions_clean',
                'development_controls',
                'quantitative_standards'
            ]

            for table in tables_to_check:
                try:
                    print(f'\n--- Checking {table} ---')
                    cur.execute(f"""
                        SELECT COUNT(*) as count
                        FROM {table}
                        WHERE provision_text ILIKE '%WAT%'
                        OR provision_text ILIKE '%CLM%'
                        OR provision_text ILIKE '%BAL%'
                        OR provision_text ILIKE '%TEW%'
                        OR provision_text ILIKE '%sustainable building%'
                    """)

                    count = cur.fetchone()['count']
                    print(f'{table}: {count} rows with SEPP map references')

                    if count > 0:
                        cur.execute(f"""
                            SELECT provision_text
                            FROM {table}
                            WHERE provision_text ILIKE '%WAT%'
                            LIMIT 1
                        """)
                        sample = cur.fetchone()
                        if sample:
                            print(f'Sample: {sample["provision_text"][:200]}...')

                except Exception as e:
                    print(f'Error checking {table}: {e}')

            print('\n=== Check for sepp_provisions table ===')
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name ILIKE '%sepp%'
                ORDER BY table_name
            """)

            sepp_tables = cur.fetchall()
            print('SEPP tables found:')
            for t in sepp_tables:
                print(f'  - {t["table_name"]}')

    except Exception as e:
        print(f'Database error: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_sepp_maps()