#!/usr/bin/env python3
"""
Check maximum lengths of string columns in SQLite
"""

import sqlite3

def check_column_lengths():
 """Check maximum lengths of string columns"""
 try:
 conn = sqlite3.connect("nsw_planning.db")
 cursor = conn.cursor()

 # Check lengths of string columns
 string_columns = [
 'document_id', 'provision_type', 'ref_number', 'provision_text',
 'zone', 'development_type', 'section_header', 'domain_classification',
 'migration_id', 'zone_inference_method'
 ]

 for col in string_columns:
 cursor.execute(f"SELECT MAX(LENGTH({col})) as max_len, {col} FROM regulatory_provisions WHERE {col} IS NOT NULL GROUP BY {col} ORDER BY max_len DESC LIMIT 5")
 results = cursor.fetchall()
 if results:
 max_len = results[0][0]
 print(f"{col}: max length = {max_len}")
 if max_len > 50: # Show examples of long values
 print(f" Example long values:")
 for result in results[:3]:
 print(f" Length {result[0]}: {result[1][:100]}...")
 print()

 conn.close()

 except Exception as e:
 print(f"Error checking column lengths: {e}")

if __name__ == "__main__":
 check_column_lengths()