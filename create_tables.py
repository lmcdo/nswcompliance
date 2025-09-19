#!/usr/bin/env python3
"""
Create BASIX and Special Provisions database tables
"""

import psycopg2
import os
from dotenv import load_dotenv

def create_tables():
    load_dotenv()

    try:
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', 5432),
            database=os.getenv('PGDATABASE', 'nsw_planning'),
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD', '')
        )

        with open('scripts/create_basix_tables.sql', 'r') as f:
            sql = f.read()

        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()

        print('✓ Database tables created successfully')

        # Verify tables were created
        cursor.execute("""
            SELECT table_name, records
            FROM (
                SELECT 'basix_provisions' as table_name, COUNT(*) as records FROM basix_provisions
                UNION ALL
                SELECT 'special_provisions_registry', COUNT(*) FROM special_provisions_registry
                UNION ALL
                SELECT 'provision_thresholds', COUNT(*) FROM provision_thresholds
                UNION ALL
                SELECT 'provision_implications', COUNT(*) FROM provision_implications
            ) t ORDER BY table_name
        """)

        results = cursor.fetchall()
        print('\nTable verification:')
        for table, count in results:
            print(f'  {table}: {count} records')

        conn.close()
        return True

    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == "__main__":
    create_tables()