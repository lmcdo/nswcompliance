#!/usr/bin/env python3
"""
Check what was actually created in PostgreSQL
"""

import psycopg2

def check_postgresql_schema():
 """Check the PostgreSQL database structure"""
 try:
 conn = psycopg2.connect(
 host="localhost",
 port=5432,
 database="nsw_planning",
 user="postgres",
 password="postgres"
 )
 cursor = conn.cursor()

 # Check if regulatory_provisions table exists
 cursor.execute("""
 SELECT table_name, column_name, data_type, is_nullable
 FROM information_schema.columns
 WHERE table_name = 'regulatory_provisions'
 ORDER BY ordinal_position
 """)

 columns = cursor.fetchall()

 if columns:
 print("REGULATORY_PROVISIONS table exists with columns:")
 for col in columns:
 print(f" {col[1]} ({col[2]}) - Nullable: {col[3]}")
 else:
 print("REGULATORY_PROVISIONS table does not exist")

 # Check all tables
 cursor.execute("""
 SELECT table_name
 FROM information_schema.tables
 WHERE table_schema = 'public'
 ORDER BY table_name
 """)

 tables = cursor.fetchall()
 print(f"\nAll tables in public schema ({len(tables)}):")
 for table in tables:
 print(f" - {table[0]}")

 conn.close()

 except Exception as e:
 print(f"Error checking PostgreSQL: {e}")

if __name__ == "__main__":
 check_postgresql_schema()