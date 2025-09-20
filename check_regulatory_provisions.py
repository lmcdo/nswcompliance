#!/usr/bin/env python3
"""Check regulatory_provisions table schema"""

import sys
import os
sys.path.append('.')
from db_config import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()

    print("regulatory_provisions table columns:")
    print("-" * 40)

    cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
    """)

    for row in cursor.fetchall():
        print(f"{row[0]:30} {row[1]}")

    print("\nSample data:")
    cursor.execute('SELECT id, zone, document_id FROM regulatory_provisions LIMIT 3')
    for row in cursor.fetchall():
        print(f'ID: {row[0]}, Zone: {row[1]}, Doc ID: {row[2]}, Type: {type(row[2])}')

    conn.close()
    print("\nSchema check complete")

except Exception as e:
    print(f"Error: {e}")