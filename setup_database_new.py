#!/usr/bin/env python3
"""
Setup PostgreSQL database for NSW Planning Compliance Engine
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_database():
 print("Setting up PostgreSQL database...")

 # Common passwords to try
 passwords = ['', 'postgres', 'admin', 'password', '123456']

 working_config = None

 # First, find working connection to postgres database
 for password in passwords:
 try:
 conn = psycopg2.connect(
 host='localhost',
 port=5433,
 database='postgres',
 user='postgres',
 password=password
 )
 print(f"Connected with password: '{password}'")
 working_config = password
 conn.close()
 break
 except Exception as e:
 print(f"Password '{password}' failed: {e}")
 continue

 if working_config is None:
 print("Could not connect to PostgreSQL. Please check password.")
 return False

 # Connect and create nsw_planning database
 try:
 conn = psycopg2.connect(
 host='localhost',
 port=5433,
 database='postgres',
 user='postgres',
 password=working_config
 )
 conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
 cursor = conn.cursor()

 # Check if nsw_planning database exists
 cursor.execute("SELECT 1 FROM pg_database WHERE datname='nsw_planning'")
 exists = cursor.fetchone()

 if not exists:
 cursor.execute("CREATE DATABASE nsw_planning")
 print("Created nsw_planning database")
 else:
 print("nsw_planning database already exists")

 conn.close()

 # Update .env file with working password
 with open('.env', 'w') as f:
 f.write(f"""# PostgreSQL Database Configuration
# PostgreSQL 17 is running on port 5433 (not default 5432)
PGHOST=localhost
PGPORT=5433
PGDATABASE=nsw_planning
PGUSER=postgres
PGPASSWORD={working_config}
""")
 print("Updated .env file with working password")

 # Now create the tables
 print("Creating BASIX and special provisions tables...")

 conn = psycopg2.connect(
 host='localhost',
 port=5433,
 database='nsw_planning',
 user='postgres',
 password=working_config
 )

 with open('scripts/create_basix_tables.sql', 'r') as f:
 sql = f.read()

 cursor = conn.cursor()
 cursor.execute(sql)
 conn.commit()

 print("Created all tables successfully")

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
 print("\nTable verification:")
 for table, count in results:
 print(f" {table}: {count} records")

 conn.close()
 return True

 except Exception as e:
 print(f"Error setting up database: {e}")
 return False

if __name__ == "__main__":
 success = setup_database()
 if success:
 print("\nDatabase setup complete! PostgreSQL is ready.")
 print("You can now run the frontend and BASIX/special provisions will work.")
 else:
 print("\nDatabase setup failed.")