#!/usr/bin/env python3
"""Check FULL database structure after Ultimate Pipeline update"""

from db_config import get_connection # Unified PostgreSQL connection
import json

# Connect to database
conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("FULL DATABASE ANALYSIS AFTER ULTIMATE PIPELINE")
print("=" * 80)

# List ALL tables
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("\nALL TABLES IN DATABASE:")
for t in tables:
 table_name = t[0]
 count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
 print(f" {table_name}: {count} rows")
 
 # Get columns for each table
 cols = cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = {table_name}").fetchall()
 print(f" Columns: {', '.join([c[1] for c in cols])}")

# Check regulatory_refs structure in detail
print("\n" + "=" * 80)
print("REGULATORY_REFS TABLE STRUCTURE:")
cols = cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = regulatory_refs").fetchall()
for col in cols:
 print(f" {col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else 'NULL OK'}")

# Sample data from regulatory_refs
print("\nSAMPLE REGULATORY_REFS DATA:")
sample = cur.execute("""
 SELECT * FROM regulatory_refs 
 WHERE page_number IS NOT NULL 
 LIMIT 2
""").fetchall()

col_names = [c[0] for c in cur.description]
for row in sample:
 print("\n Record:")
 for i, val in enumerate(row):
 if val and len(str(val)) > 100:
 print(f" {col_names[i]}: {str(val)[:100]}...")
 else:
 print(f" {col_names[i]}: {val}")

# Check if there are other entity/relationship tables
print("\n" + "=" * 80)
print("ENTITY/RELATIONSHIP TABLES:")
for t in tables:
 table_name = t[0]
 if 'entity' in table_name.lower() or 'relation' in table_name.lower() or 'provision' in table_name.lower():
 count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
 print(f"\n {table_name}: {count} rows")
 
 # Sample one row
 sample = cur.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchall()
 if sample:
 col_names = [c[0] for c in cur.description]
 print(f" Columns: {', '.join(col_names)}")
 print(f" Sample: {sample[0][:3]}..." if len(sample[0]) > 3 else f" Sample: {sample[0]}")

# Check for any KG or graph tables
print("\n" + "=" * 80)
print("KNOWLEDGE GRAPH TABLES:")
for t in tables:
 table_name = t[0]
 if 'kg' in table_name.lower() or 'graph' in table_name.lower() or 'node' in table_name.lower() or 'edge' in table_name.lower():
 count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
 print(f" {table_name}: {count} rows")

# Statistics
print("\n" + "=" * 80)
print("DATABASE STATISTICS:")
total_refs = cur.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
with_pages = cur.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL").fetchone()[0]
unique_docs = cur.execute("SELECT COUNT(DISTINCT document_id) FROM regulatory_refs").fetchone()[0]

print(f" Total regulatory references: {total_refs:,}")
print(f" References with page numbers: {with_pages:,} ({with_pages/total_refs*100:.1f}%)")
print(f" Unique documents: {unique_docs}")

# Check what ref_types exist
print("\nREFERENCE TYPES IN DATABASE:")
ref_types = cur.execute("SELECT DISTINCT ref_type, COUNT(*) FROM regulatory_refs GROUP BY ref_type").fetchall()
for rt in ref_types:
 print(f" {rt[0]}: {rt[1]:,} entries")

conn.close()