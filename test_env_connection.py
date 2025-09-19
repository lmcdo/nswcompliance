#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Environment variables:")
print(f"PGHOST: {os.getenv('PGHOST', 'not set')}")
print(f"PGPORT: {os.getenv('PGPORT', 'not set')}")
print(f"PGDATABASE: {os.getenv('PGDATABASE', 'not set')}")
print(f"PGUSER: {os.getenv('PGUSER', 'not set')}")
print(f"PGPASSWORD: {os.getenv('PGPASSWORD', 'not set')}")

try:
    conn = psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', 5432)),
        database=os.getenv('PGDATABASE', 'postgres'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', '')
    )
    print(f"\n✅ SUCCESS: Connected using .env variables!")
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()[0]
    print(f"PostgreSQL version: {version.split()[1]}")

    # Check if nsw_planning database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='nsw_planning'")
    db_exists = cursor.fetchone()
    print(f"nsw_planning database exists: {bool(db_exists)}")

    conn.close()
except Exception as e:
    print(f"\n❌ FAILED: {e}")