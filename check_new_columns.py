#!/usr/bin/env python3
"""Check the new columns in the database including page numbers"""

import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()

# Check regulatory_refs table structure
print("regulatory_refs table columns:")
cols = cur.execute('PRAGMA table_info(regulatory_refs)').fetchall()
for col in cols:
 print(f' {col[1]} ({col[2]})')

# Check for page_number and other new columns
print("\nSample data with new columns:")
sample = cur.execute('''
 SELECT document_id, ref_number, page_number, section_header, extraction_timestamp 
 FROM regulatory_refs 
 WHERE page_number IS NOT NULL 
 LIMIT 5
''').fetchall()

for row in sample:
 print(f" Doc: {row[0]}, Ref: {row[1]}, Page: {row[2]}, Section: {row[3]}, Timestamp: {row[4]}")

conn.close()