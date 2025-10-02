#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

try:
    conn = get_dict_connection()
    cursor = conn.cursor()

    print("=== POSTGRESQL SEPP DATA CHECK ===")

    # Check sepp_lep_overrides table structure
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'sepp_lep_overrides'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print("sepp_lep_overrides table columns:")
    for col in columns:
        print(f"  {col['column_name']} ({col['data_type']})")

    # Get count and sample data
    cursor.execute("SELECT COUNT(*) as count FROM sepp_lep_overrides")
    count = cursor.fetchone()
    print(f"\nSEPP override records: {count['count']}")

    if count['count'] > 0:
        cursor.execute("SELECT * FROM sepp_lep_overrides LIMIT 5")
        samples = cursor.fetchall()
        print("\nSample SEPP override records:")
        for i, sample in enumerate(samples):
            print(f"  Record {i+1}: {dict(sample)}")

    # Check regulatory_provisions table structure
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
        ORDER BY ordinal_position
    """)
    prov_columns = cursor.fetchall()
    print("\nregulatory_provisions table columns:")
    for col in prov_columns:
        print(f"  {col['column_name']} ({col['data_type']})")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
