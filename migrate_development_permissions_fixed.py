#!/usr/bin/env python3
"""
Fixed migration of development_permissions from SQLite to PostgreSQL
"""
import sqlite3
import psycopg2

def migrate_development_permissions():
 # Connect to SQLite
 sqlite_conn = sqlite3.connect('nsw_planning.db')
 sqlite_cursor = sqlite_conn.cursor()

 # Get all data
 sqlite_cursor.execute('SELECT * FROM development_permissions')
 all_data = sqlite_cursor.fetchall()
 print(f"Found {len(all_data)} development permissions to migrate")

 # Connect to PostgreSQL
 pg_conn = psycopg2.connect(
 host='localhost',
 port=5432,
 database='nsw_planning',
 user='postgres',
 password='postgres'
 )
 pg_cursor = pg_conn.cursor()

 # Create table in PostgreSQL with correct schema
 pg_cursor.execute('''
 DROP TABLE IF EXISTS development_permissions;
 CREATE TABLE development_permissions (
 id SERIAL PRIMARY KEY,
 zone VARCHAR(10),
 development_type VARCHAR(200),
 permission_status VARCHAR(50),
 conditions TEXT,
 source_provision_id INTEGER,
 lep_name VARCHAR(500),
 extraction_method VARCHAR(100),
 confidence_score VARCHAR(100), -- Keep as VARCHAR to handle text values
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 source_type VARCHAR(100)
 );
 ''')

 # Insert data with proper handling
 success_count = 0
 for i, row in enumerate(all_data):
 try:
 # Map SQLite row: id, zone, development_type, permission_status, conditions, source_provision_id,
 # lep_name, extraction_method, confidence_score, created_at, source_type
 pg_cursor.execute('''
 INSERT INTO development_permissions
 (zone, development_type, permission_status, conditions, source_provision_id,
 lep_name, extraction_method, confidence_score, source_type)
 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
 ''', (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[10]))

 success_count += 1
 if success_count % 50 == 0:
 print(f"Migrated {success_count}/{len(all_data)} development permissions")

 except Exception as e:
 print(f"Error migrating row {i}: {e}")
 print(f"Row data: {row}")
 # Continue with next row instead of failing

 pg_conn.commit()

 # Verify migration
 pg_cursor.execute('SELECT COUNT(*) FROM development_permissions')
 pg_count = pg_cursor.fetchone()[0]
 print(f"Successfully migrated {pg_count} development permissions to PostgreSQL")

 # Show sample data
 pg_cursor.execute('SELECT zone, development_type, permission_status FROM development_permissions LIMIT 5')
 sample = pg_cursor.fetchall()
 print("Sample migrated data:")
 for zone, dev_type, status in sample:
 print(f" {zone}: {dev_type} = {status}")

 sqlite_conn.close()
 pg_conn.close()

if __name__ == '__main__':
 migrate_development_permissions()