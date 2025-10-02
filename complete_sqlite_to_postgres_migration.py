#!/usr/bin/env python3

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import json
from datetime import datetime
import traceback

class SQLiteToPostgreSQLMigration:
    def __init__(self):
        self.sqlite_db = 'nsw_planning.db'
        self.postgres_config = {
            'host': 'localhost',
            'database': 'nsw_planning',
            'user': 'postgres',
            'password': 'postgres',
            'port': '5432'
        }

    def get_sqlite_connection(self):
        """Get SQLite database connection"""
        return sqlite3.connect(self.sqlite_db)

    def get_postgres_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.postgres_config)

    def analyze_sqlite_structure(self):
        """Analyze the SQLite database structure"""
        print('=== ANALYZING SQLITE DATABASE STRUCTURE ===')

        with self.get_sqlite_connection() as sqlite_conn:
            cursor = sqlite_conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            table_info = {}
            total_rows = 0

            for table in tables:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                total_rows += count

                # Get column info
                cursor.execute(f"PRAGMA table_info(`{table}`)")
                columns = cursor.fetchall()

                table_info[table] = {
                    'rows': count,
                    'columns': columns
                }

                print(f'{table}: {count:,} rows, {len(columns)} columns')

            print(f'\nTotal tables: {len(tables)}')
            print(f'Total rows: {total_rows:,}')

            return table_info

    def create_postgres_schema(self, table_info):
        """Create PostgreSQL tables with proper schema"""
        print('\n=== CREATING POSTGRESQL SCHEMA ===')

        with self.get_postgres_connection() as pg_conn:
            with pg_conn.cursor() as cursor:

                # Type mapping from SQLite to PostgreSQL
                type_mapping = {
                    'INTEGER': 'INTEGER',
                    'TEXT': 'TEXT',
                    'REAL': 'REAL',
                    'BLOB': 'BYTEA',
                    'NUMERIC': 'NUMERIC',
                    'VARCHAR': 'VARCHAR',
                    'BOOLEAN': 'BOOLEAN',
                    'TIMESTAMP': 'TIMESTAMP',
                    'DATE': 'DATE',
                    'JSONB': 'JSONB'
                }

                for table_name, info in table_info.items():
                    if info['rows'] == 0:
                        print(f'Skipping empty table: {table_name}')
                        continue

                    print(f'Creating table: {table_name}')

                    # Drop table if exists
                    cursor.execute(f'DROP TABLE IF EXISTS public."{table_name}" CASCADE')

                    # Build CREATE TABLE statement
                    columns = []
                    for col in info['columns']:
                        col_id, col_name, col_type, not_null, default_value, pk = col

                        # Map SQLite type to PostgreSQL
                        pg_type = type_mapping.get(col_type.upper(), 'TEXT')

                        # Handle primary key
                        if pk:
                            pg_type = 'SERIAL PRIMARY KEY' if pg_type == 'INTEGER' else f'{pg_type} PRIMARY KEY'

                        # Handle NOT NULL
                        null_clause = ' NOT NULL' if not_null and not pk else ''

                        # Handle DEFAULT
                        default_clause = f' DEFAULT {default_value}' if default_value else ''

                        columns.append(f'"{col_name}" {pg_type}{null_clause}{default_clause}')

                    create_sql = f'''
                    CREATE TABLE public."{table_name}" (
                        {', '.join(columns)}
                    )
                    '''

                    try:
                        cursor.execute(create_sql)
                        print(f'  ✓ Created table {table_name}')
                    except Exception as e:
                        print(f'  ✗ Error creating table {table_name}: {e}')

                pg_conn.commit()

    def migrate_table_data(self, table_name, batch_size=1000):
        """Migrate data from SQLite table to PostgreSQL"""
        print(f'\n--- Migrating {table_name} ---')

        try:
            with self.get_sqlite_connection() as sqlite_conn:
                sqlite_cursor = sqlite_conn.cursor()

                # Get total rows
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                total_rows = sqlite_cursor.fetchone()[0]

                if total_rows == 0:
                    print(f'  No data to migrate for {table_name}')
                    return

                print(f'  Migrating {total_rows:,} rows...')

                # Get column names
                sqlite_cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = [col[1] for col in sqlite_cursor.fetchall()]

                with self.get_postgres_connection() as pg_conn:
                    with pg_conn.cursor() as pg_cursor:

                        # Clear existing data
                        pg_cursor.execute(f'TRUNCATE TABLE public."{table_name}" RESTART IDENTITY CASCADE')

                        # Migrate in batches
                        offset = 0
                        migrated = 0

                        while offset < total_rows:
                            # Fetch batch from SQLite
                            sqlite_cursor.execute(f'''
                                SELECT {', '.join([f'`{col}`' for col in columns])}
                                FROM `{table_name}`
                                LIMIT {batch_size} OFFSET {offset}
                            ''')

                            batch_data = sqlite_cursor.fetchall()

                            if not batch_data:
                                break

                            # Prepare insert statement
                            placeholders = ', '.join(['%s'] * len(columns))
                            insert_sql = f'''
                                INSERT INTO public."{table_name}" ({', '.join([f'"{col}"' for col in columns])})
                                VALUES ({placeholders})
                            '''

                            # Convert data for PostgreSQL
                            converted_data = []
                            for row in batch_data:
                                converted_row = []
                                for value in row:
                                    # Handle JSON strings
                                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                                        try:
                                            json.loads(value)
                                            converted_row.append(value)
                                        except:
                                            converted_row.append(value)
                                    else:
                                        converted_row.append(value)
                                converted_data.append(tuple(converted_row))

                            # Insert batch
                            execute_values(pg_cursor, insert_sql, converted_data, page_size=batch_size)

                            migrated += len(batch_data)
                            offset += batch_size

                            print(f'    Progress: {migrated:,}/{total_rows:,} ({100*migrated/total_rows:.1f}%)')

                        pg_conn.commit()
                        print(f'  ✓ Successfully migrated {migrated:,} rows')

                        # Update sequence if needed (for SERIAL columns)
                        try:
                            pg_cursor.execute(f'''
                                SELECT column_name FROM information_schema.columns
                                WHERE table_name = '{table_name}'
                                AND column_default LIKE 'nextval%'
                            ''')
                            serial_columns = pg_cursor.fetchall()

                            for col in serial_columns:
                                col_name = col[0]
                                pg_cursor.execute(f'''
                                    SELECT setval(pg_get_serial_sequence('public."{table_name}"', '{col_name}'),
                                                 COALESCE(MAX("{col_name}"), 1))
                                    FROM public."{table_name}"
                                ''')
                                pg_conn.commit()
                        except:
                            pass  # Sequences will be handled automatically

        except Exception as e:
            print(f'  ✗ Error migrating {table_name}: {e}')
            traceback.print_exc()

    def create_indexes(self):
        """Create essential indexes for performance"""
        print('\n=== CREATING INDEXES ===')

        index_definitions = [
            ('regulatory_provisions', 'document_id'),
            ('regulatory_provisions', 'provision_type'),
            ('regulatory_provisions', 'zone'),
            ('development_controls', 'control_type'),
            ('development_controls', 'zone_applicable'),
            ('kg_entities', 'entity_type'),
            ('kg_relationships', 'predicate'),
            ('quantitative_standards', 'numeric_value'),
            ('visual_elements_real', 'document_id'),
        ]

        with self.get_postgres_connection() as pg_conn:
            with pg_conn.cursor() as cursor:
                for table, column in index_definitions:
                    try:
                        cursor.execute(f'''
                            CREATE INDEX IF NOT EXISTS idx_{table}_{column}
                            ON public."{table}" ("{column}")
                        ''')
                        print(f'  ✓ Created index on {table}.{column}')
                    except Exception as e:
                        print(f'  ✗ Index creation failed for {table}.{column}: {e}')

                pg_conn.commit()

    def verify_migration(self):
        """Verify the migration was successful"""
        print('\n=== VERIFYING MIGRATION ===')

        with self.get_sqlite_connection() as sqlite_conn:
            sqlite_cursor = sqlite_conn.cursor()

            with self.get_postgres_connection() as pg_conn:
                with pg_conn.cursor() as pg_cursor:

                    # Get table counts from both databases
                    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                    tables = [row[0] for row in sqlite_cursor.fetchall()]

                    total_sqlite = 0
                    total_postgres = 0

                    print('Table verification:')
                    for table in tables:
                        # SQLite count
                        sqlite_cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                        sqlite_count = sqlite_cursor.fetchone()[0]
                        total_sqlite += sqlite_count

                        # PostgreSQL count
                        try:
                            pg_cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
                            pg_count = pg_cursor.fetchone()[0]
                            total_postgres += pg_count

                            status = "✓" if sqlite_count == pg_count else "✗"
                            print(f'  {status} {table}: SQLite {sqlite_count:,} → PostgreSQL {pg_count:,}')

                        except Exception as e:
                            print(f'  ✗ {table}: PostgreSQL table missing or error: {e}')

                    print(f'\nTotal verification:')
                    print(f'  SQLite total: {total_sqlite:,} rows')
                    print(f'  PostgreSQL total: {total_postgres:,} rows')
                    print(f'  Migration success: {100*total_postgres/total_sqlite:.1f}%' if total_sqlite > 0 else 'No data to migrate')

    def run_complete_migration(self):
        """Run the complete migration process"""
        start_time = datetime.now()
        print(f'=== STARTING COMPLETE SQLITE TO POSTGRESQL MIGRATION ===')
        print(f'Started at: {start_time}')
        print(f'Source: {self.sqlite_db}')
        print(f'Target: PostgreSQL {self.postgres_config["database"]}')
        print()

        try:
            # Step 1: Analyze SQLite structure
            table_info = self.analyze_sqlite_structure()

            # Step 2: Create PostgreSQL schema
            self.create_postgres_schema(table_info)

            # Step 3: Migrate data for populated tables
            populated_tables = [name for name, info in table_info.items() if info['rows'] > 0]
            print(f'\n=== MIGRATING DATA FOR {len(populated_tables)} POPULATED TABLES ===')

            for table_name in populated_tables:
                self.migrate_table_data(table_name)

            # Step 4: Create indexes
            self.create_indexes()

            # Step 5: Verify migration
            self.verify_migration()

            end_time = datetime.now()
            duration = end_time - start_time

            print(f'\n=== MIGRATION COMPLETED ===')
            print(f'Total time: {duration}')
            print(f'Completed at: {end_time}')

        except Exception as e:
            print(f'\n=== MIGRATION FAILED ===')
            print(f'Error: {e}')
            traceback.print_exc()

def main():
    migration = SQLiteToPostgreSQLMigration()
    migration.run_complete_migration()

if __name__ == "__main__":
    main()