#!/usr/bin/env python3
"""
Verify the successful migration of data from SQLite to PostgreSQL
"""

import sqlite3
import psycopg2
import json

def verify_migration():
 """Verify the migration was successful"""

 # Check SQLite count
 sqlite_conn = sqlite3.connect("nsw_planning.db")
 sqlite_cursor = sqlite_conn.cursor()
 sqlite_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
 sqlite_count = sqlite_cursor.fetchone()[0]
 sqlite_conn.close()

 # Check PostgreSQL count
 pg_conn = psycopg2.connect(
 host="localhost",
 port=5432,
 database="nsw_planning",
 user="postgres",
 password="postgres"
 )
 pg_cursor = pg_conn.cursor()
 pg_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
 pg_count = pg_cursor.fetchone()[0]

 # Sample some data to verify structure
 pg_cursor.execute("""
 SELECT document_id, provision_type, ref_number, provision_text,
 zone, development_type, page_number
 FROM regulatory_provisions
 LIMIT 5
 """)
 sample_data = pg_cursor.fetchall()

 # Check data distribution
 pg_cursor.execute("SELECT zone, COUNT(*) FROM regulatory_provisions GROUP BY zone ORDER BY COUNT(*) DESC LIMIT 10")
 zone_distribution = pg_cursor.fetchall()

 pg_cursor.execute("SELECT provision_type, COUNT(*) FROM regulatory_provisions WHERE provision_type IS NOT NULL GROUP BY provision_type ORDER BY COUNT(*) DESC LIMIT 10")
 type_distribution = pg_cursor.fetchall()

 pg_conn.close()

 print("="*60)
 print("MIGRATION VERIFICATION RESULTS")
 print("="*60)
 print(f"SQLite source records: {sqlite_count:,}")
 print(f"PostgreSQL target records: {pg_count:,}")
 print(f"Migration success: {' YES' if sqlite_count == pg_count else ' NO'}")

 print(f"\nSample migrated data:")
 for i, row in enumerate(sample_data):
 print(f"Row {i+1}:")
 print(f" Document: {row[0]}")
 print(f" Type: {row[1]}")
 print(f" Ref: {row[2]}")
 print(f" Text: {row[3][:100]}...")
 print(f" Zone: {row[4]}")
 print()

 print("Zone distribution (top 10):")
 for zone, count in zone_distribution:
 print(f" {zone or 'NULL'}: {count:,} records")

 print("\nProvision type distribution (top 10):")
 for ptype, count in type_distribution:
 print(f" {ptype}: {count:,} records")

 # Save verification results
 results = {
 "sqlite_count": sqlite_count,
 "postgresql_count": pg_count,
 "migration_successful": sqlite_count == pg_count,
 "zone_distribution": dict(zone_distribution),
 "type_distribution": dict(type_distribution)
 }

 with open("migration_verification_results.json", "w") as f:
 json.dump(results, f, indent=2)

 print(f"\n Migration verification complete - results saved to migration_verification_results.json")
 return sqlite_count == pg_count

if __name__ == "__main__":
 verify_migration()