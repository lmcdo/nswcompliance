#!/usr/bin/env python3
"""Investigate the sepp_structured_requirements FK constraint."""
import os
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=== sepp_structured_requirements Table ===")

# Get table structure
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'sepp_structured_requirements'
    ORDER BY ordinal_position
""")
print("\nColumns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")

# Get all rows
cur.execute("SELECT * FROM sepp_structured_requirements LIMIT 10")
columns = [desc[0] for desc in cur.description]
print(f"\nData ({len(columns)} columns):")
print(f"  Columns: {columns}")
rows = cur.fetchall()
print(f"  Rows: {len(rows)}")

for row in rows:
    print(f"\n  Row:")
    for i, col in enumerate(columns):
        val = row[i]
        if val is not None:
            val_str = str(val)[:80] if len(str(val)) > 80 else str(val)
            print(f"    {col}: {val_str}")

# Check which provisions are referenced
cur.execute("""
    SELECT
        ssr.source_provision_id,
        rp.document_id,
        LEFT(rp.provision_text, 100) as text_preview
    FROM sepp_structured_requirements ssr
    JOIN regulatory_provisions rp ON ssr.source_provision_id = rp.id
""")
print("\n\n=== Referenced Provisions ===")
for row in cur.fetchall():
    print(f"\n  ID {row[0]}:")
    print(f"    Doc: {row[1][:60]}")
    print(f"    Text: {row[2]}...")

# Check if these are in duplicate docs we want to delete
cur.execute("""
    SELECT
        rp.document_id,
        COUNT(*) as refs
    FROM sepp_structured_requirements ssr
    JOIN regulatory_provisions rp ON ssr.source_provision_id = rp.id
    GROUP BY rp.document_id
""")
print("\n\n=== Documents with FK References ===")
for row in cur.fetchall():
    print(f"  {row[0][:60]}: {row[1]} refs")

conn.close()
