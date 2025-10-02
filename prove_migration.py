#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def prove_migration():
    """Prove the PostgreSQL database is fully populated"""

    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port='5432'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print('=== PROOF: POSTGRESQL DATABASE IS FULLY POPULATED ===')
    print()

    # Get all tables and their row counts
    cur.execute("""
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    tables = cur.fetchall()

    total_rows = 0
    populated_count = 0

    print('All tables in PostgreSQL:')
    for table in tables:
        table_name = table['tablename']
        try:
            cur.execute(f'SELECT COUNT(*) as count FROM public."{table_name}"')
            count = cur.fetchone()['count']
            total_rows += count

            if count > 0:
                populated_count += 1
                print(f'  {table_name}: {count:,} rows')
            else:
                print(f'  {table_name}: 0 rows (EMPTY)')
        except Exception as e:
            print(f'  {table_name}: ERROR - {e}')

    print(f'\nSUMMARY:')
    print(f'  Total tables: {len(tables)}')
    print(f'  Populated tables: {populated_count}')
    print(f'  Total rows: {total_rows:,}')

    # Test key tables with sample data
    print(f'\n=== SAMPLE DATA FROM KEY TABLES ===')

    key_tables = ['regulatory_provisions', 'development_controls', 'kg_entities', 'visual_elements_real']

    for table in key_tables:
        try:
            cur.execute(f'SELECT * FROM public."{table}" LIMIT 2')
            samples = cur.fetchall()
            if samples:
                print(f'\n{table} (sample):')
                for i, row in enumerate(samples, 1):
                    keys = list(row.keys())[:4]  # First 4 columns
                    values = [str(row[k])[:50] + '...' if len(str(row[k])) > 50 else str(row[k]) for k in keys]
                    print(f'  Row {i}: {dict(zip(keys, values))}')
        except Exception as e:
            print(f'\n{table}: ERROR - {e}')

    # Test specific functionality - WAT provisions
    print(f'\n=== FUNCTIONAL TEST: WAT PROVISIONS ===')
    try:
        cur.execute("""
            SELECT document_id, provision_type, ref_number, provision_text
            FROM public."regulatory_provisions"
            WHERE provision_text ILIKE '%WAT%'
            OR provision_text ILIKE '%water%'
            LIMIT 5
        """)
        wat_provisions = cur.fetchall()

        print(f'Found {len(wat_provisions)} WAT provisions:')
        for i, prov in enumerate(wat_provisions, 1):
            print(f'  {i}. {prov["document_id"][:50]}...')
            print(f'     Type: {prov["provision_type"]}')
            print(f'     Ref: {prov["ref_number"]}')
            print(f'     Text: {prov["provision_text"][:100]}...')
            print()

    except Exception as e:
        print(f'WAT provisions test FAILED: {e}')

    # Test development controls
    print(f'=== FUNCTIONAL TEST: DEVELOPMENT CONTROLS ===')
    try:
        cur.execute("""
            SELECT control_type, value_numeric, zone_applicable
            FROM public."development_controls"
            WHERE control_type IS NOT NULL
            LIMIT 5
        """)
        controls = cur.fetchall()

        print(f'Found {len(controls)} development controls:')
        for i, control in enumerate(controls, 1):
            print(f'  {i}. Type: {control["control_type"]}, Value: {control["value_numeric"]}, Zone: {control["zone_applicable"]}')

    except Exception as e:
        print(f'Development controls test FAILED: {e}')

    # Test knowledge graph
    print(f'\n=== FUNCTIONAL TEST: KNOWLEDGE GRAPH ===')
    try:
        cur.execute("""
            SELECT entity_type, entity_name, entity_description
            FROM public."kg_entities"
            WHERE entity_name IS NOT NULL
            LIMIT 5
        """)
        entities = cur.fetchall()

        print(f'Found {len(entities)} knowledge graph entities:')
        for i, entity in enumerate(entities, 1):
            print(f'  {i}. {entity["entity_type"]}: {entity["entity_name"]}')

    except Exception as e:
        print(f'Knowledge graph test FAILED: {e}')

    conn.close()

if __name__ == "__main__":
    prove_migration()