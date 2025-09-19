#!/usr/bin/env python3
"""
PostgreSQL Database Configuration
Standard connection parameters to prevent connection failures
"""

import psycopg2
import os

# Standard PostgreSQL connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nsw_planning',
    'user': 'postgres',
    'password': 'postgres'
}

def get_connection():
    """Get a PostgreSQL connection using standard parameters"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        print(f"Using config: {DB_CONFIG}")
        raise

def test_connection():
    """Test database connection and return status"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        conn.close()
        return True, version[0]
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    success, result = test_connection()
    if success:
        print("SUCCESS: Database connection successful")
        print(f"PostgreSQL version: {result[:50]}...")
    else:
        print(f"FAILED: Database connection failed: {result}")