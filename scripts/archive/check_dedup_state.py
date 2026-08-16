#!/usr/bin/env python3
"""Check state after partial deduplication."""
import os
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=== SEPP State After Partial Deduplication ===")
cur.execute("""
    SELECT COUNT(DISTINCT document_id) as docs, COUNT(*) as provisions
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sepp%' OR document_id ILIKE '%state_environmental%'
""")
row = cur.fetchone()
print(f"Total: {row[0]} documents, {row[1]} provisions")

print("\n=== Remaining Documents ===")
cur.execute("""
    SELECT document_id, COUNT(*) as provisions
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sepp%' OR document_id ILIKE '%state_environmental%'
    GROUP BY document_id
    ORDER BY provisions DESC
""")
for row in cur.fetchall():
    print(f"  {row[1]:>5} provisions: {row[0][:60]}")

print("\n=== Foreign Key Table ===")
cur.execute("SELECT COUNT(*) FROM sepp_structured_requirements")
print(f"sepp_structured_requirements: {cur.fetchone()[0]} rows")

conn.close()
