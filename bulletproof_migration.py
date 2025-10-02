#!/usr/bin/env python3

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys
from datetime import datetime

class BulletproofMigration:
    def __init__(self):
        self.sqlite_db = 'nsw_planning.db'
        self.postgres_config = {
            'host': 'localhost',
            'database': 'nsw_planning',
            'user': 'postgres',
            'password': 'postgres',
            'port': '5432'
        }

    def log(self, message):
        """Safe logging without unicode issues"""
        try:
            print(message)
        except:
            print(message.encode('ascii', 'ignore').decode('ascii'))

    def get_populated_tables(self):
        """Get only tables with data from SQLite"""
        with sqlite3.connect(self.sqlite_db) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]

            populated_tables = []
            for table in all_tables:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                if count > 0:
                    populated_tables.append((table, count))

            return populated_tables

    def drop_and_recreate_table(self, table_name):
        """Drop and recreate table with flexible schema"""
        with psycopg2.connect(**self.postgres_config) as pg_conn:
            with pg_conn.cursor() as cursor:
                # Drop existing table
                cursor.execute(f'DROP TABLE IF EXISTS public."{table_name}" CASCADE')

                # Get SQLite schema
                with sqlite3.connect(self.sqlite_db) as sqlite_conn:
                    sqlite_cursor = sqlite_conn.cursor()
                    sqlite_cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                    columns = sqlite_cursor.fetchall()

                # Create PostgreSQL table with TEXT columns (safest approach)
                pg_columns = []
                for col in columns:
                    col_id, col_name, col_type, not_null, default_value, pk = col

                    if pk and col_type.upper() == 'INTEGER':
                        pg_columns.append(f'"{col_name}" SERIAL PRIMARY KEY')
                    else:
                        pg_columns.append(f'"{col_name}" TEXT')

                create_sql = f'CREATE TABLE public."{table_name}" ({", ".join(pg_columns)})'
                cursor.execute(create_sql)
                pg_conn.commit()

    def migrate_table_data_simple(self, table_name, row_count):
        """Simple, reliable data migration"""
        self.log(f"Migrating {table_name} ({row_count:,} rows)...")

        try:
            # Recreate table
            self.drop_and_recreate_table(table_name)

            with sqlite3.connect(self.sqlite_db) as sqlite_conn:
                sqlite_cursor = sqlite_conn.cursor()

                # Get all data
                sqlite_cursor.execute(f"SELECT * FROM `{table_name}`")
                all_data = sqlite_cursor.fetchall()

                # Get column names
                sqlite_cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = [col[1] for col in sqlite_cursor.fetchall()]

                with psycopg2.connect(**self.postgres_config) as pg_conn:
                    with pg_conn.cursor() as pg_cursor:

                        if all_data:
                            # Convert all values to strings to avoid type issues
                            safe_data = []
                            for row in all_data:
                                safe_row = []
                                for value in row:
                                    if value is None:
                                        safe_row.append(None)
                                    else:
                                        # Convert everything to string
                                        safe_row.append(str(value))
                                safe_data.append(tuple(safe_row))

                            # Insert in batches
                            batch_size = 1000
                            for i in range(0, len(safe_data), batch_size):
                                batch = safe_data[i:i+batch_size]

                                placeholders = ', '.join(['%s'] * len(columns))
                                insert_sql = f'''
                                    INSERT INTO public."{table_name}"
                                    ({', '.join([f'"{col}"' for col in columns])})
                                    VALUES ({placeholders})
                                '''

                                execute_values(pg_cursor, insert_sql, batch, page_size=batch_size)

                                if i % 5000 == 0:
                                    self.log(f"  Progress: {i:,}/{len(safe_data):,}")

                            pg_conn.commit()

                        # Verify count
                        pg_cursor.execute(f'SELECT COUNT(*) FROM public."{table_name}"')
                        pg_count = pg_cursor.fetchone()[0]

                        if pg_count == row_count:
                            self.log(f"  SUCCESS: {table_name} ({pg_count:,} rows)")
                            return True
                        else:
                            self.log(f"  WARNING: {table_name} count mismatch - SQLite: {row_count:,}, PostgreSQL: {pg_count:,}")
                            return False

        except Exception as e:
            self.log(f"  ERROR migrating {table_name}: {str(e)}")
            return False

    def run_migration(self):
        """Run the bulletproof migration"""
        start_time = datetime.now()
        self.log("=== BULLETPROOF SQLITE TO POSTGRESQL MIGRATION ===")
        self.log(f"Started: {start_time}")

        # Get populated tables
        populated_tables = self.get_populated_tables()
        self.log(f"Found {len(populated_tables)} populated tables")

        # Sort by size (migrate smaller tables first)
        populated_tables.sort(key=lambda x: x[1])

        success_count = 0
        fail_count = 0

        for table_name, row_count in populated_tables:
            if self.migrate_table_data_simple(table_name, row_count):
                success_count += 1
            else:
                fail_count += 1

        # Create essential indexes
        self.log("\nCreating indexes...")
        self.create_basic_indexes()

        # Final verification
        self.verify_migration_simple(populated_tables)

        end_time = datetime.now()
        duration = end_time - start_time

        self.log(f"\n=== MIGRATION COMPLETE ===")
        self.log(f"Duration: {duration}")
        self.log(f"Success: {success_count} tables")
        self.log(f"Failed: {fail_count} tables")

    def create_basic_indexes(self):
        """Create essential indexes"""
        indexes = [
            ('regulatory_provisions', 'document_id'),
            ('regulatory_provisions', 'provision_type'),
            ('development_controls', 'control_type'),
            ('kg_entities', 'entity_type'),
        ]

        with psycopg2.connect(**self.postgres_config) as pg_conn:
            with pg_conn.cursor() as cursor:
                for table, column in indexes:
                    try:
                        cursor.execute(f'''
                            CREATE INDEX IF NOT EXISTS idx_{table}_{column.replace('.', '_')}
                            ON public."{table}" ("{column}")
                        ''')
                        self.log(f"  Index created: {table}.{column}")
                    except:
                        pass
                pg_conn.commit()

    def verify_migration_simple(self, expected_tables):
        """Simple verification"""
        self.log("\n=== VERIFICATION ===")

        with psycopg2.connect(**self.postgres_config) as pg_conn:
            with pg_conn.cursor() as cursor:
                total_expected = sum(count for _, count in expected_tables)
                total_actual = 0

                for table_name, expected_count in expected_tables:
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM public."{table_name}"')
                        actual_count = cursor.fetchone()[0]
                        total_actual += actual_count

                        status = "OK" if actual_count == expected_count else "MISMATCH"
                        self.log(f"  {table_name}: {actual_count:,} ({status})")

                    except Exception as e:
                        self.log(f"  {table_name}: ERROR - {str(e)}")

                self.log(f"\nTotal: {total_actual:,}/{total_expected:,} rows migrated")
                success_rate = 100 * total_actual / total_expected if total_expected > 0 else 0
                self.log(f"Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    migration = BulletproofMigration()
    migration.run_migration()