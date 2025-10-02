#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def generate_complete_db_report():
    """Generate comprehensive database structure and data report"""

    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            report = {
                'generated_at': datetime.now().isoformat(),
                'database': 'nsw_planning',
                'tables': {},
                'summary': {}
            }

            print('=== COMPREHENSIVE NSW PLANNING DATABASE REPORT ===')
            print(f'Generated at: {report["generated_at"]}')
            print()

            # 1. Get all tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            tables = cur.fetchall()
            table_names = [t['table_name'] for t in tables]

            print(f'=== DATABASE OVERVIEW ===')
            print(f'Total Tables: {len(table_names)}')
            print(f'Tables: {", ".join(table_names)}')
            print()

            # 2. Analyze each table
            for table_name in table_names:
                print(f'=== TABLE: {table_name.upper()} ===')

                table_info = {
                    'columns': [],
                    'row_count': 0,
                    'sample_data': [],
                    'indexes': [],
                    'constraints': []
                }

                # Get column information
                cur.execute("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))

                columns = cur.fetchall()
                table_info['columns'] = [dict(col) for col in columns]

                print('Columns:')
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                    length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                    print(f"  - {col['column_name']}: {col['data_type']}{length} {nullable}{default}")

                # Get row count
                try:
                    cur.execute(f'SELECT COUNT(*) as count FROM "{table_name}"')
                    count_result = cur.fetchone()
                    table_info['row_count'] = count_result['count']
                    print(f'Row Count: {table_info["row_count"]:,}')
                except Exception as e:
                    print(f'Row Count: Error - {e}')
                    table_info['row_count'] = 0

                # Get sample data (first 5 rows)
                try:
                    cur.execute(f'SELECT * FROM "{table_name}" LIMIT 5')
                    sample_rows = cur.fetchall()
                    table_info['sample_data'] = [dict(row) for row in sample_rows]

                    if sample_rows:
                        print('Sample Data (first 5 rows):')
                        for i, row in enumerate(sample_rows, 1):
                            print(f'  Row {i}:')
                            for key, value in row.items():
                                # Truncate long values
                                if isinstance(value, str) and len(value) > 100:
                                    value = value[:100] + "..."
                                print(f'    {key}: {value}')
                            print()
                except Exception as e:
                    print(f'Sample Data: Error - {e}')

                # Get indexes
                try:
                    cur.execute("""
                        SELECT indexname, indexdef
                        FROM pg_indexes
                        WHERE tablename = %s
                    """, (table_name,))
                    indexes = cur.fetchall()
                    table_info['indexes'] = [dict(idx) for idx in indexes]

                    if indexes:
                        print('Indexes:')
                        for idx in indexes:
                            print(f"  - {idx['indexname']}: {idx['indexdef']}")
                except Exception as e:
                    print(f'Indexes: Error - {e}')

                # Get constraints
                try:
                    cur.execute("""
                        SELECT constraint_name, constraint_type
                        FROM information_schema.table_constraints
                        WHERE table_name = %s
                    """, (table_name,))
                    constraints = cur.fetchall()
                    table_info['constraints'] = [dict(c) for c in constraints]

                    if constraints:
                        print('Constraints:')
                        for constraint in constraints:
                            print(f"  - {constraint['constraint_name']}: {constraint['constraint_type']}")
                except Exception as e:
                    print(f'Constraints: Error - {e}')

                report['tables'][table_name] = table_info
                print()

            # 3. Generate summary statistics
            total_rows = sum(t['row_count'] for t in report['tables'].values())
            largest_table = max(report['tables'].items(), key=lambda x: x[1]['row_count'])

            report['summary'] = {
                'total_tables': len(table_names),
                'total_rows': total_rows,
                'largest_table': {
                    'name': largest_table[0],
                    'rows': largest_table[1]['row_count']
                },
                'tables_by_size': sorted(
                    [(name, info['row_count']) for name, info in report['tables'].items()],
                    key=lambda x: x[1],
                    reverse=True
                )
            }

            print('=== SUMMARY STATISTICS ===')
            print(f'Total Tables: {report["summary"]["total_tables"]}')
            print(f'Total Rows: {report["summary"]["total_rows"]:,}')
            print(f'Largest Table: {report["summary"]["largest_table"]["name"]} ({report["summary"]["largest_table"]["rows"]:,} rows)')
            print()
            print('Tables by Size:')
            for table, count in report['summary']['tables_by_size']:
                print(f'  - {table}: {count:,} rows')
            print()

            # 4. Key data analysis for SEPP provisions
            print('=== KEY DATA ANALYSIS ===')

            # Analyze regulatory provisions
            if 'regulatory_provisions' in table_names:
                try:
                    cur.execute("""
                        SELECT document_id, COUNT(*) as provision_count
                        FROM regulatory_provisions
                        GROUP BY document_id
                        ORDER BY provision_count DESC
                        LIMIT 10
                    """)
                    top_documents = cur.fetchall()

                    print('Top 10 Documents by Provision Count:')
                    for doc in top_documents:
                        print(f'  - {doc["document_id"]}: {doc["provision_count"]} provisions')
                    print()

                    # Analyze provision types
                    cur.execute("""
                        SELECT provision_type, COUNT(*) as count
                        FROM regulatory_provisions
                        WHERE provision_type IS NOT NULL
                        GROUP BY provision_type
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    provision_types = cur.fetchall()

                    print('Top Provision Types:')
                    for ptype in provision_types:
                        print(f'  - {ptype["provision_type"]}: {ptype["count"]} provisions')
                    print()

                except Exception as e:
                    print(f'Regulatory provisions analysis error: {e}')

            # Analyze knowledge graph entities
            if 'kg_entities' in table_names:
                try:
                    cur.execute("""
                        SELECT entity_type, COUNT(*) as count
                        FROM kg_entities
                        GROUP BY entity_type
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    entity_types = cur.fetchall()

                    print('Knowledge Graph Entity Types:')
                    for etype in entity_types:
                        print(f'  - {etype["entity_type"]}: {etype["count"]} entities')
                    print()

                except Exception as e:
                    print(f'Knowledge graph analysis error: {e}')

            # Save report to file
            with open('database_structure_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)

            print('=== REPORT SAVED ===')
            print('Full report saved to: database_structure_report.json')
            print()

            return report

    except Exception as e:
        print(f'Database connection error: {e}')
        return None
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    result = generate_complete_db_report()
    if result:
        print('Database report generation completed successfully.')
    else:
        print('Database report generation failed.')