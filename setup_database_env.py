#!/usr/bin/env python3
"""
Setup PostgreSQL database using .env configuration
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def setup_database():
 print("Setting up PostgreSQL database using .env configuration...")

 # Load environment variables
 load_dotenv()

 config = {
 'host': os.getenv('PGHOST', 'localhost'),
 'port': int(os.getenv('PGPORT', 5432)),
 'user': os.getenv('PGUSER', 'postgres'),
 'password': os.getenv('PGPASSWORD', '')
 }

 print(f"Connecting to PostgreSQL at {config['host']}:{config['port']} as {config['user']}")

 # Try to connect to postgres database first
 try:
 conn = psycopg2.connect(
 host=config['host'],
 port=config['port'],
 database='postgres',
 user=config['user'],
 password=config['password']
 )
 conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
 cursor = conn.cursor()

 print(" Connected to PostgreSQL successfully!")

 # Check if nsw_planning database exists
 cursor.execute("SELECT 1 FROM pg_database WHERE datname='nsw_planning'")
 exists = cursor.fetchone()

 target_db = os.getenv('PGDATABASE', 'nsw_planning')

 if not exists:
 cursor.execute(f"CREATE DATABASE {target_db}")
 print(f" Created {target_db} database")
 else:
 print(f" {target_db} database already exists")

 conn.close()

 # Now connect to the nsw_planning database and create tables
 print("Creating BASIX and special provisions tables...")

 conn = psycopg2.connect(
 host=config['host'],
 port=config['port'],
 database=target_db,
 user=config['user'],
 password=config['password']
 )

 # Read and execute the SQL schema
 schema_file = 'scripts/create_basix_tables.sql'
 if os.path.exists(schema_file):
 with open(schema_file, 'r') as f:
 sql = f.read()

 cursor = conn.cursor()
 cursor.execute(sql)
 conn.commit()

 print(" Created all tables successfully")

 # Verify tables
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
 print("\n Table verification:")
 for table, count in results:
 print(f" {table}: {count} records")

 conn.close()

 else:
 print(f" Schema file not found: {schema_file}")
 conn.close()
 return False

 return True

 except Exception as e:
 print(f" Error setting up database: {e}")
 return False

if __name__ == "__main__":
 success = setup_database()
 if success:
 print("\n Database setup complete! PostgreSQL is ready.")
 print("You can now run the frontend and BASIX/special provisions will work.")
 else:
 print("\n Database setup failed.")