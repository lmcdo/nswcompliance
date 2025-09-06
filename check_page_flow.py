#!/usr/bin/env python3
"""Check if page numbers are flowing through the system"""

import sqlite3

# Connect to database
conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()

# Check sample data with page numbers
print("Sample data with page numbers:")
sample = cur.execute('''
    SELECT document_id, ref_number, page_number, section_header, text_level 
    FROM regulatory_refs 
    WHERE page_number IS NOT NULL 
    LIMIT 5
''').fetchall()

for row in sample:
    print(f"  Doc: {row[0][:30]}...")
    print(f"  Ref: {row[1]}")  
    print(f"  Page: {row[2]}")
    print(f"  Section: {row[3]}")
    print(f"  Level: {row[4]}")
    print("-" * 40)

# Check statistics
total = cur.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
with_pages = cur.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL").fetchone()[0]

print(f"\nStatistics:")
print(f"Total entries: {total}")
print(f"With page numbers: {with_pages} ({with_pages/total*100:.1f}%)")

conn.close()