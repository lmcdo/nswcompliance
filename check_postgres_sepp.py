#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

try:
    conn = get_dict_connection()
    cursor = conn.cursor()

    print("=== POSTGRESQL DATABASE SEPP CHECK ===")

    # Check for SEPP-related tables
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE '%sepp%'
        ORDER BY table_name
    """)
    sepp_tables = cursor.fetchall()
    print(f"SEPP-related tables: {len(sepp_tables)}")
    for table in sepp_tables:
        print(f"  {table['table_name']}")

    # Check for regulatory_provisions table
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE content ILIKE '%SEPP%'
        OR clause_number ILIKE '%SEPP%'
        OR clause_title ILIKE '%SEPP%'
    """)
    sepp_provisions = cursor.fetchone()
    print(f"\nSEPP mentions in regulatory_provisions: {sepp_provisions['count']}")

    # Sample SEPP provisions
    if sepp_provisions['count'] > 0:
        cursor.execute("""
            SELECT clause_number, clause_title, content
            FROM regulatory_provisions
            WHERE content ILIKE '%SEPP%'
            OR clause_number ILIKE '%SEPP%'
            OR clause_title ILIKE '%SEPP%'
            LIMIT 3
        """)
        samples = cursor.fetchall()
        print("\nSample SEPP provisions:")
        for sample in samples:
            content = sample['content'][:150] + '...' if sample['content'] and len(sample['content']) > 150 else sample['content']
            print(f"  {sample['clause_number']}: {sample['clause_title']}")
            print(f"    {content}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
    print("Make sure PostgreSQL is running and database exists")
