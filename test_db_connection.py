#!/usr/bin/env python3
"""
Test PostgreSQL database connection
"""

import psycopg2

def test_connection():
    # PostgreSQL connection parameters - using standard port 5432
    test_configs = [
        {'host': 'localhost', 'port': 5432, 'database': 'postgres', 'user': 'postgres', 'password': ''},
        {'host': 'localhost', 'port': 5432, 'database': 'nsw_planning', 'user': 'postgres', 'password': ''},
        {'host': 'localhost', 'port': 5432, 'database': 'postgres', 'user': 'postgres', 'password': 'postgres'},
        {'host': 'localhost', 'port': 5432, 'database': 'nsw_planning', 'user': 'postgres', 'password': 'postgres'},
    ]

    for i, config in enumerate(test_configs, 1):
        print(f"\nTest {i}: {config}")
        try:
            conn = psycopg2.connect(**config)
            print(f"✓ Connected successfully!")

            cursor = conn.cursor()
            cursor.execute('SELECT version();')
            version = cursor.fetchone()
            print(f"PostgreSQL version: {version[0][:50]}...")

            # Check if nsw_planning database exists
            if config['database'] == 'postgres':
                cursor.execute("SELECT 1 FROM pg_database WHERE datname='nsw_planning'")
                db_exists = cursor.fetchone()
                print(f"nsw_planning database exists: {bool(db_exists)}")

            conn.close()
            return config

        except Exception as e:
            print(f"X Connection failed: {e}")

    return None

if __name__ == "__main__":
    print("Testing PostgreSQL Connection...")
    working_config = test_connection()

    if working_config:
        print(f"\n✓ WORKING CONFIG: {working_config}")
    else:
        print("\n✗ No working configuration found")