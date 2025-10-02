#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check table_parsing_results structure
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'table_parsing_results'
    ORDER BY ordinal_position
""")

print("=== table_parsing_results schema ===\n")
for col, dtype in cur.fetchall():
    print(f"  {col:30} {dtype}")

# Get sample table data
cur.execute("""
    SELECT *
    FROM table_parsing_results
    LIMIT 3
""")

print("\n=== Sample table_parsing_results records ===")
for row in cur.fetchall():
    print(f"\nRecord: {row[:5]}...")  # First 5 fields

conn.close()
