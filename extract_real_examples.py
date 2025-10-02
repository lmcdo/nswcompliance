#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def extract_real_examples():
    """Extract real examples from each table in PostgreSQL"""

    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port='5432'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print('=== REAL DATA EXAMPLES FROM EACH TABLE ===')
    print()

    # Get all populated tables
    cur.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    tables = [row['tablename'] for row in cur.fetchall()]

    for table_name in tables:
        try:
            # Get row count
            cur.execute(f'SELECT COUNT(*) as count FROM public."{table_name}"')
            count = cur.fetchone()['count']

            if count == 0:
                print(f'=== {table_name.upper()} ===')
                print('Status: EMPTY TABLE')
                print()
                continue

            print(f'=== {table_name.upper()} ({count:,} rows) ===')

            # Get column names
            cur.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}' AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            col_names = [col['column_name'] for col in columns]

            print(f'Columns: {", ".join(col_names[:8])}...' if len(col_names) > 8 else f'Columns: {", ".join(col_names)}')

            # Get 2 real examples
            cur.execute(f'SELECT * FROM public."{table_name}" LIMIT 2')
            examples = cur.fetchall()

            for i, example in enumerate(examples, 1):
                print(f'\nExample {i}:')
                for col_name in col_names[:6]:  # Show first 6 columns
                    value = example.get(col_name, 'N/A')
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + '...'
                    print(f'  {col_name}: {value}')

            print()

        except Exception as e:
            print(f'=== {table_name.upper()} ===')
            print(f'Error: {e}')
            print()

    # Now show some specific interesting examples
    print('=== SPECIFIC INTERESTING EXAMPLES ===')
    print()

    # WAT provisions
    print('WAT PROVISIONS:')
    try:
        cur.execute("""
            SELECT document_id, provision_type, ref_number, provision_text
            FROM public."regulatory_provisions"
            WHERE provision_text ILIKE '%water use map%'
            LIMIT 3
        """)
        wat_provisions = cur.fetchall()

        for i, prov in enumerate(wat_provisions, 1):
            print(f'{i}. Document: {prov["document_id"][:60]}...')
            print(f'   Type: {prov["provision_type"]}')
            print(f'   Reference: {prov["ref_number"]}')
            print(f'   Text: {prov["provision_text"][:150]}...')
            print()
    except Exception as e:
        print(f'Error getting WAT provisions: {e}')

    # Development controls with numbers
    print('DEVELOPMENT CONTROLS (with numeric values):')
    try:
        cur.execute("""
            SELECT control_type, control_subtype, value_numeric, unit, zone_applicable
            FROM public."development_controls"
            WHERE value_numeric IS NOT NULL
            LIMIT 5
        """)
        controls = cur.fetchall()

        for i, control in enumerate(controls, 1):
            print(f'{i}. Type: {control["control_type"]}, Subtype: {control["control_subtype"]}')
            print(f'   Value: {control["value_numeric"]} {control["unit"] or ""}')
            print(f'   Zone: {control["zone_applicable"]}')
            print()
    except Exception as e:
        print(f'Error getting development controls: {e}')

    # Knowledge graph relationships
    print('KNOWLEDGE GRAPH RELATIONSHIPS:')
    try:
        cur.execute("""
            SELECT subject_text, predicate, object_text
            FROM public."kg_relationships"
            WHERE subject_text IS NOT NULL
            LIMIT 5
        """)
        relationships = cur.fetchall()

        for i, rel in enumerate(relationships, 1):
            print(f'{i}. "{rel["subject_text"]}" {rel["predicate"]} "{rel["object_text"]}"')
    except Exception as e:
        print(f'Error getting KG relationships: {e}')

    conn.close()

if __name__ == "__main__":
    extract_real_examples()