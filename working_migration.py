#!/usr/bin/env python3

import sqlite3
import psycopg2

def migrate():
    sqlite_db = 'nsw_planning.db'
    pg_config = {
        'host': 'localhost',
        'database': 'nsw_planning', 
        'user': 'postgres',
        'password': 'postgres',
        'port': '5432'
    }

    print('Starting migration...')
    
    with sqlite3.connect(sqlite_db) as sqlite_conn:
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        populated_tables = []
        for table in all_tables:
            sqlite_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = sqlite_cursor.fetchone()[0]
            if count > 0:
                populated_tables.append((table, count))
    
    print(f'Found {len(populated_tables)} tables with data')
    
    with psycopg2.connect(**pg_config) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            for table_name, row_count in populated_tables:
                print(f'Migrating {table_name} ({row_count} rows)...')
                try:
                    pg_cursor.execute(f'DROP TABLE IF EXISTS public."{table_name}" CASCADE')
                    
                    with sqlite3.connect(sqlite_db) as sqlite_conn:
                        sqlite_cursor = sqlite_conn.cursor()
                        
                        sqlite_cursor.execute(f'PRAGMA table_info("{table_name}")')
                        columns = sqlite_cursor.fetchall()
                        
                        pg_columns = []
                        col_names = []
                        for col in columns:
                            col_id, col_name, col_type, not_null, default_value, pk = col
                            col_names.append(col_name)
                            if pk and col_type.upper() == 'INTEGER':
                                pg_columns.append(f'"{col_name}" SERIAL PRIMARY KEY')
                            else:
                                pg_columns.append(f'"{col_name}" TEXT')
                        
                        create_sql = f'CREATE TABLE public."{table_name}" ({", ".join(pg_columns)})'
                        pg_cursor.execute(create_sql)
                        
                        sqlite_cursor.execute(f'SELECT * FROM "{table_name}"')
                        rows = sqlite_cursor.fetchall()
                        
                        for i, row in enumerate(rows):
                            safe_values = [str(v) if v is not None else None for v in row]
                            placeholders = ', '.join(['%s'] * len(col_names))
                            quoted_cols = ', '.join([f'"{col}"' for col in col_names])
                            insert_sql = f'INSERT INTO public."{table_name}" ({quoted_cols}) VALUES ({placeholders})'
                            pg_cursor.execute(insert_sql, safe_values)
                            
                            if (i + 1) % 1000 == 0:
                                print(f'  Progress: {i+1}/{len(rows)}')
                        
                        pg_conn.commit()
                        print(f'  SUCCESS: {table_name}')
                        
                except Exception as e:
                    print(f'  FAILED: {table_name} - {str(e)}')
                    pg_conn.rollback()
    
    print('Migration completed')

if __name__ == '__main__':
    migrate()
