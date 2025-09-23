#!/usr/bin/env python3
"""
Migrate development_permissions from SQLite to PostgreSQL
"""
import sqlite3
import psycopg2

def migrate_development_permissions():
 # Connect to SQLite
 sqlite_conn = sqlite3.connect('nsw_planning.db')
 sqlite_cursor = sqlite_conn.cursor()

 # Get SQLite schema and data
 sqlite_cursor.execute('PRAGMA table_info(development_permissions)')
 columns_info = sqlite_cursor.fetchall()
 column_names = [col[1] for col in columns_info]
 print(f"SQLite columns: {column_names}")

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

 # Create table in PostgreSQL with simplified schema
 pg_cursor.execute('''
 DROP TABLE IF EXISTS development_permissions;
 CREATE TABLE development_permissions (
 id SERIAL PRIMARY KEY,
 zone VARCHAR(10),
 development_type VARCHAR(200),
 permission_status VARCHAR(50),
 lep_name VARCHAR(200),
 clause_reference VARCHAR(100),
 extraction_method VARCHAR(100),
 confidence_score DECIMAL(3,2),
 source_type VARCHAR(100),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 );
 ''')

 # Insert data
 for i, row in enumerate(all_data):
 # Map SQLite columns to PostgreSQL columns (adjust as needed)
 try:
 pg_cursor.execute('''
 INSERT INTO development_permissions
 (zone, development_type, permission_status, lep_name, clause_reference,
 extraction_method, confidence_score, source_type)
 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 ''', row[1:9]) # Skip the id column from SQLite

 if (i + 1) % 50 == 0:
 print(f"Migrated {i + 1}/{len(all_data)} development permissions")
 except Exception as e:
 print(f"Error migrating row {i}: {e}")
 print(f"Row data: {row}")

 pg_conn.commit()

 # Verify migration
 pg_cursor.execute('SELECT COUNT(*) FROM development_permissions')
 pg_count = pg_cursor.fetchone()[0]
 print(f"Successfully migrated {pg_count} development permissions to PostgreSQL")

 sqlite_conn.close()
 pg_conn.close()

if __name__ == '__main__':
 migrate_development_permissions()