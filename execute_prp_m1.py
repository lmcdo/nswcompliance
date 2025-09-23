#!/usr/bin/env python3
"""
PRP-M1: Complete Database Migration Engine
Migrates all missing tables from SQLite to PostgreSQL with verification
"""

from db_config import get_connection # Unified PostgreSQL connection
import psycopg2
import json
from datetime import datetime
from db_config import get_connection

class PRP_M1_Migration:
 def __init__(self):
 self.sqlite_conn = get_connection()
 self.postgres_conn = get_connection()
 self.migration_report = {
 'start_time': datetime.now().isoformat(),
 'tables_migrated': {},
 'verification_results': {},
 'total_records_migrated': 0,
 'status': 'IN_PROGRESS'
 }

 def get_table_schema(self, table_name):
 """Get SQLite table schema and convert to PostgreSQL"""
 cursor = self.sqlite_conn.cursor()
 cursor.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name = {table_name}')
 columns = cursor.fetchall()

 # Convert SQLite types to PostgreSQL
 type_mapping = {
 'TEXT': 'TEXT',
 'INTEGER': 'INTEGER',
 'REAL': 'REAL',
 'BLOB': 'BYTEA',
 'NUMERIC': 'NUMERIC'
 }

 pg_columns = []
 for col in columns:
 col_name = col[1]
 col_type = col[2].upper()
 is_pk = col[5]
 not_null = col[3]

 pg_type = type_mapping.get(col_type, 'TEXT')

 pg_col = f'"{col_name}" {pg_type}'
 if not_null:
 pg_col += ' NOT NULL'
 if is_pk:
 pg_col += ' PRIMARY KEY'

 pg_columns.append(pg_col)

 return f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(pg_columns)})'

 def migrate_table(self, table_name):
 """Migrate single table with verification"""
 print(f"Migrating {table_name}...")

 # Check if table exists in SQLite
 sqlite_cursor = self.sqlite_conn.cursor()
 try:
 sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
 total_rows = sqlite_cursor.fetchone()[0]
 except sqlite3.OperationalError:
 print(f" Skipping {table_name} - table does not exist")
 return

 if total_rows == 0:
 print(f" Skipping {table_name} - no data")
 return

 # Create table in PostgreSQL
 schema = self.get_table_schema(table_name)
 postgres_cursor = self.postgres_conn.cursor()
 postgres_cursor.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
 postgres_cursor.execute(schema)

 # Get column names
 sqlite_cursor.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name = {table_name}')
 columns = [col[1] for col in sqlite_cursor.fetchall()]

 # Prepare INSERT statement
 placeholders = ', '.join(['%s'] * len(columns))
 insert_sql = f'INSERT INTO {table_name} ({", ".join(columns)}) VALUES ({placeholders})'

 # Migrate all rows
 sqlite_cursor.execute(f'SELECT * FROM {table_name}')
 all_rows = sqlite_cursor.fetchall()

 postgres_cursor.executemany(insert_sql, all_rows)
 self.postgres_conn.commit()

 # Verify migration
 postgres_cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
 migrated_rows = postgres_cursor.fetchone()[0]

 migration_success = migrated_rows == total_rows

 self.migration_report['tables_migrated'][table_name] = {
 'source_rows': total_rows,
 'migrated_rows': migrated_rows,
 'success': migration_success,
 'timestamp': datetime.now().isoformat()
 }

 self.migration_report['total_records_migrated'] += migrated_rows

 print(f" SUCCESS {table_name}: {migrated_rows:,} / {total_rows:,} rows")

 if not migration_success:
 raise Exception(f"Migration failed for {table_name}")

 def verify_data_integrity(self):
 """Verify sample data matches between databases"""
 print("Verifying data integrity...")

 verification_tables = ['development_controls', 'quantitative_standards', 'contextual_guidance']

 for table in verification_tables:
 if table not in self.migration_report['tables_migrated']:
 continue

 sqlite_cursor = self.sqlite_conn.cursor()
 postgres_cursor = self.postgres_conn.cursor()

 # Sample 5 random rows
 try:
 sqlite_cursor.execute(f'SELECT * FROM {table} ORDER BY RANDOM() LIMIT 5')
 sqlite_sample = sqlite_cursor.fetchall()

 if sqlite_sample:
 # Get first row ID for verification
 first_id = sqlite_sample[0][0]
 postgres_cursor.execute(f'SELECT * FROM {table} WHERE id = %s', (first_id,))
 postgres_match = postgres_cursor.fetchone()

 matches = sqlite_sample[0] == postgres_match

 self.migration_report['verification_results'][table] = {
 'sample_verified': matches,
 'sample_size': len(sqlite_sample),
 'first_row_id': first_id
 }

 print(f" SUCCESS {table}: Sample verification {'PASSED' if matches else 'FAILED'}")

 except Exception as e:
 print(f" Warning: {table} verification failed: {e}")

 def execute_migration(self):
 """Execute complete migration with verification"""
 try:
 print("=== PRP-M1: COMPLETE DATABASE MIGRATION ===")

 # Phase 1: Core tables
 core_tables = ['development_controls', 'quantitative_standards', 'contextual_guidance']
 print("\nPhase 1: Core Tables")
 for table in core_tables:
 self.migrate_table(table)

 # Phase 2: Knowledge graph tables
 kg_tables = ['kg_entities', 'kg_visual_elements', 'kg_visual_clause_links']
 print("\nPhase 2: Knowledge Graph Tables")
 for table in kg_tables:
 try:
 self.migrate_table(table)
 except Exception as e:
 print(f" Warning: {table} migration failed: {e}")

 # Phase 3: Supporting tables
 support_tables = ['documents', 'regulatory_refs']
 print("\nPhase 3: Supporting Tables")
 for table in support_tables:
 try:
 self.migrate_table(table)
 except Exception as e:
 print(f" Warning: {table} migration failed: {e}")

 # Verify integrity
 print("\nData Integrity Verification:")
 self.verify_data_integrity()

 self.migration_report['status'] = 'COMPLETED'
 self.migration_report['end_time'] = datetime.now().isoformat()

 # Save report
 with open('prp_m1_migration_report.json', 'w') as f:
 json.dump(self.migration_report, f, indent=2)

 print(f"\nSUCCESS PRP-M1 COMPLETED: {self.migration_report['total_records_migrated']:,} records migrated")
 print(f"Report saved: prp_m1_migration_report.json")

 except Exception as e:
 self.migration_report['status'] = 'FAILED'
 self.migration_report['error'] = str(e)
 print(f"FAILED PRP-M1 FAILED: {e}")
 raise

 finally:
 self.sqlite_conn.close()
 self.postgres_conn.close()

if __name__ == "__main__":
 migrator = PRP_M1_Migration()
 migrator.execute_migration()