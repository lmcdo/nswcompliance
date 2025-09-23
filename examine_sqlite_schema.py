#!/usr/bin/env python3
"""
Examine SQLite database schema to identify column mismatches
"""

import sqlite3
import json

def examine_sqlite_schema():
 """Examine the SQLite database structure"""
 db_path = "nsw_planning.db"

 try:
 conn = sqlite3.connect(db_path)
 cursor = conn.cursor()

 # Get all table names
 cursor.execute("""
 SELECT name FROM sqlite_master
 WHERE type='table'
 AND name NOT LIKE 'sqlite_%'
 ORDER BY name
 """)
 tables = [row[0] for row in cursor.fetchall()]

 print(f"Found {len(tables)} tables in SQLite database:")
 for table in tables:
 print(f" - {table}")

 # Examine regulatory_provisions table specifically
 if 'regulatory_provisions' in tables:
 print("\n" + "="*60)
 print("REGULATORY_PROVISIONS TABLE STRUCTURE:")
 print("="*60)

 # Get column info
 cursor.execute("PRAGMA table_info(regulatory_provisions)")
 columns = cursor.fetchall()

 print("Columns:")
 for col in columns:
 print(f" {col[1]} ({col[2]}) - NOT NULL: {bool(col[3])} - Default: {col[4]} - PK: {bool(col[5])}")

 # Get sample data
 cursor.execute("SELECT * FROM regulatory_provisions LIMIT 3")
 sample_data = cursor.fetchall()

 print(f"\nSample data (first 3 rows):")
 for i, row in enumerate(sample_data):
 print(f"Row {i+1}: {row}")

 # Get count
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
 count = cursor.fetchone()[0]
 print(f"\nTotal records: {count}")

 else:
 print("\nERROR: regulatory_provisions table not found!")

 conn.close()

 except Exception as e:
 print(f"Error examining SQLite database: {e}")

if __name__ == "__main__":
 examine_sqlite_schema()