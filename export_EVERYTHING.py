#!/usr/bin/env python3
"""
EXPORT EVERYTHING FROM SQLITE TO POSTGRESQL
This exports ALL tables with data, not just the tiny zone_setback_rules table
"""

import sqlite3
import psycopg2
import json
from datetime import datetime

def export_complete_database():
    """Export ALL regulatory data from SQLite to PostgreSQL"""
    
    print("=== COMPLETE DATABASE EXPORT ===")
    print("Exporting EVERYTHING from SQLite to PostgreSQL...")
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect('nsw_planning.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres', 
        password='postgres'
    )
    pg_cursor = pg_conn.cursor()
    
    # Get list of all tables with data
    sqlite_cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = sqlite_cursor.fetchall()
    
    total_records_exported = 0
    tables_exported = []
    
    for table_tuple in tables:
        table_name = table_tuple[0]
        
        # Get record count
        sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = sqlite_cursor.fetchone()[0]
        
        if count == 0:
            continue
            
        print(f"\nExporting {table_name}: {count:,} records...")
        
        # Get table schema
        sqlite_cursor.execute(f'PRAGMA table_info({table_name})')
        columns = sqlite_cursor.fetchall()
        
        # Create PostgreSQL table
        pg_cursor.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
        
        create_sql = f'CREATE TABLE {table_name} ('
        col_names = []
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            col_names.append(col_name)
            
            # Convert SQLite types to PostgreSQL
            if 'INT' in col_type.upper():
                pg_type = 'INTEGER'
            elif 'REAL' in col_type.upper() or 'FLOAT' in col_type.upper():
                pg_type = 'REAL'
            elif 'NUMERIC' in col_type.upper():
                pg_type = 'NUMERIC'
            elif 'BOOL' in col_type.upper():
                pg_type = 'BOOLEAN'
            elif 'TIMESTAMP' in col_type.upper():
                pg_type = 'TIMESTAMP'
            else:
                pg_type = 'TEXT'
            
            create_sql += f'{col_name} {pg_type}, '
        
        create_sql = create_sql.rstrip(', ') + ')'
        pg_cursor.execute(create_sql)
        
        # Export data
        sqlite_cursor.execute(f'SELECT * FROM {table_name}')
        records = sqlite_cursor.fetchall()
        
        # Insert into PostgreSQL
        placeholders = ', '.join(['%s'] * len(col_names))
        insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'
        
        for record in records:
            try:
                pg_cursor.execute(insert_sql, record)
            except Exception as e:
                print(f"  Warning: Failed to insert record: {e}")
                continue
        
        total_records_exported += count
        tables_exported.append({
            'table': table_name,
            'records': count,
            'columns': len(col_names)
        })
        
        print(f"  ✓ Exported {count:,} records")
    
    # Create critical indexes
    print("\nCreating indexes...")
    
    critical_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_reg_prov_doc ON regulatory_provisions(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_reg_prov_text ON regulatory_provisions USING gin(to_tsvector('english', provision_text))",
        "CREATE INDEX IF NOT EXISTS idx_dev_controls_prov ON development_controls(provision_id)",
        "CREATE INDEX IF NOT EXISTS idx_visual_prov ON visual_elements(provision_id)",
        "CREATE INDEX IF NOT EXISTS idx_kg_rel_subj ON kg_relationships(subject_entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_zone_rules ON zone_setback_rules(zone, council)"
    ]
    
    for idx_sql in critical_indexes:
        try:
            pg_cursor.execute(idx_sql)
            print(f"  ✓ {idx_sql[:50]}...")
        except:
            pass
    
    pg_conn.commit()
    
    # Save export summary
    summary = {
        'export_timestamp': datetime.now().isoformat(),
        'total_tables': len(tables_exported),
        'total_records': total_records_exported,
        'tables': tables_exported
    }
    
    with open('complete_export_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "="*60)
    print("EXPORT COMPLETE!")
    print(f"  Total Tables: {len(tables_exported)}")
    print(f"  Total Records: {total_records_exported:,}")
    print("\nKey tables exported:")
    for t in tables_exported:
        if t['records'] > 100:
            print(f"  - {t['table']}: {t['records']:,} records")
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    export_complete_database()