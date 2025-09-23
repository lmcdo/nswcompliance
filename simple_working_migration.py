#!/usr/bin/env python3
"""
Simple Working Migration Script
Migrates SQLite data to compatible PostgreSQL schema
No arrays, no complex transformations - just direct field mapping
"""

from db_config import get_connection # Unified PostgreSQL connection
import psycopg2
import sys
from datetime import datetime

def migrate_sqlite_to_postgres():
 """Migrate data from SQLite to compatible PostgreSQL schema"""
 
 print("SIMPLE WORKING MIGRATION")
 print("=" * 50)
 
 # Connect to SQLite source
 print("Connecting to SQLite source...")
 sqlite_conn = get_connection()
 sqlite_cursor = sqlite_conn.cursor()
 
 # Connect to PostgreSQL target
 print("Connecting to PostgreSQL target...")
 pg_conn = psycopg2.connect(
 host='localhost',
 database='nsw_planning', 
 user='postgres',
 password='postgres'
 )
 pg_cursor = pg_conn.cursor()
 
 # Get provisions with zones and development types
 print("Loading source provisions...")
 sqlite_cursor.execute("""
 SELECT 
 zone,
 development_type,
 provision_text,
 ref_number,
 document_id,
 section_header,
 provision_type,
 classification_confidence
 FROM regulatory_provisions 
 WHERE zone IS NOT NULL 
 LIMIT 100
 """)
 
 provisions = sqlite_cursor.fetchall()
 print(f"Found Found {len(provisions)} provisions to migrate")
 
 # Migrate provisions
 success_count = 0
 failure_count = 0
 
 for i, provision in enumerate(provisions):
 try:
 zone, dev_type, text, ref_num, doc_id, section, prov_type, confidence = provision
 
 # Insert into PostgreSQL with direct field mapping
 pg_cursor.execute("""
 INSERT INTO public.regulatory_provisions (
 zone, development_type, provision_text, ref_number, 
 document_id, section_header, provision_type, confidence_score
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 RETURNING id
 """, (
 zone, dev_type, text, ref_num, 
 doc_id, section, prov_type, confidence or 0.85
 ))
 
 provision_id = pg_cursor.fetchone()[0]
 success_count += 1
 
 if i % 10 == 0:
 print(f"SUCCESS Progress: {i+1}/{len(provisions)} - Success: {success_count}, Failed: {failure_count}")
 
 except Exception as e:
 failure_count += 1
 print(f"ERROR Error migrating provision {i+1}: {e}")
 continue
 
 # Commit the transaction
 pg_conn.commit()
 
 # Final statistics
 print("\n" + "=" * 50)
 print("STATS MIGRATION COMPLETE")
 print(f"SUCCESS Successful: {success_count}")
 print(f"ERROR Failed: {failure_count}")
 print(f"Rate Success Rate: {success_count/(success_count+failure_count)*100:.1f}%")
 
 # Verify the migration
 print("\nVERIFY VERIFICATION:")
 pg_cursor.execute("SELECT COUNT(*) FROM public.regulatory_provisions")
 total_count = pg_cursor.fetchone()[0]
 print(f"Found Total provisions in PostgreSQL: {total_count}")
 
 pg_cursor.execute("SELECT zone, COUNT(*) FROM public.regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY count DESC LIMIT 5")
 zones = pg_cursor.fetchall()
 print("ZONES Top zones:")
 for zone, count in zones:
 print(f" {zone}: {count} provisions")
 
 # Close connections
 sqlite_conn.close()
 pg_conn.close()
 
 return success_count > 0

if __name__ == "__main__":
 try:
 success = migrate_sqlite_to_postgres()
 if success:
 print("\nSUCCESS MIGRATION SUCCESSFUL!")
 sys.exit(0)
 else:
 print("\nFAILED MIGRATION FAILED!")
 sys.exit(1)
 except Exception as e:
 print(f"\nFAILED MIGRATION CRASHED: {e}")
 sys.exit(1)