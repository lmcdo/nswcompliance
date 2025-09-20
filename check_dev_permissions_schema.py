#!/usr/bin/env python3
"""Check development_permissions table schema"""

import sys
import os
sys.path.append('.')
from db_config import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()

    print("development_permissions table schema:")
    print("-" * 60)

    cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'development_permissions'
    ORDER BY ordinal_position
    """)

    for row in cursor.fetchall():
        print(f"{row[0]:25} {row[1]:20} {row[2]:10} {row[3] or ''}")

    print("\nSample data:")
    print("-" * 60)
    cursor.execute("SELECT * FROM development_permissions LIMIT 3")
    columns = [desc[0] for desc in cursor.description]
    print(" | ".join(f"{col:15}" for col in columns))
    print("-" * (16 * len(columns)))

    for row in cursor.fetchall():
        print(" | ".join(f"{str(val)[:15]:15}" for val in row))

    conn.close()
    print("\n✅ Schema analysis complete")

except Exception as e:
    print(f"❌ Error: {e}")