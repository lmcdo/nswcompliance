#!/usr/bin/env python3
"""
Migrate Quantitative Standards - THE MISSING PIECE
Migrates the actual setback measurements that the frontend needs
"""

import sqlite3
import psycopg2
import sys

def migrate_quantitative_standards():
 """Migrate the quantitative setback data that was missing"""
 
 print("MIGRATING QUANTITATIVE STANDARDS")
 print("=" * 50)
 
 # Connect to SQLite source
 sqlite_conn = sqlite3.connect('nsw_planning.db')
 sqlite_cursor = sqlite_conn.cursor()
 
 # Connect to PostgreSQL target
 pg_conn = psycopg2.connect(
 host='localhost',
 database='nsw_planning', 
 user='postgres',
 password='postgres'
 )
 pg_cursor = pg_conn.cursor()
 
 # Get quantitative standards for existing provisions
 print("Loading quantitative standards...")
 sqlite_cursor.execute("""
 SELECT 
 qs.id,
 qs.provision_id,
 qs.numeric_value,
 qs.unit,
 qs.qualifier,
 qs.context,
 qs.confidence_score,
 qs.manual_verified,
 qs.raw_text,
 qs.created_timestamp
 FROM quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE rp.zone IS NOT NULL
 AND qs.context LIKE '%setback%'
 LIMIT 200
 """)
 
 standards = sqlite_cursor.fetchall()
 print(f"Found {len(standards)} quantitative standards to migrate")
 
 # Create mapping of old provision IDs to new provision IDs
 print("Creating provision ID mapping...")
 sqlite_cursor.execute("SELECT id, zone, provision_text FROM regulatory_provisions WHERE zone IS NOT NULL LIMIT 100")
 sqlite_provisions = sqlite_cursor.fetchall()
 
 id_mapping = {}
 for old_id, zone, text in sqlite_provisions:
 # Find corresponding PostgreSQL provision
 pg_cursor.execute("""
 SELECT id FROM public.regulatory_provisions 
 WHERE zone = %s AND provision_text = %s LIMIT 1
 """, (zone, text))
 
 result = pg_cursor.fetchone()
 if result:
 id_mapping[old_id] = result[0]
 
 print(f"Created mapping for {len(id_mapping)} provisions")
 
 # Migrate quantitative standards
 success_count = 0
 failure_count = 0
 
 for i, standard in enumerate(standards):
 try:
 old_id, old_prov_id, numeric_value, unit, qualifier, context, confidence, verified, raw_text, created = standard
 
 # Get new provision ID
 new_prov_id = id_mapping.get(old_prov_id)
 if not new_prov_id:
 continue
 
 # Insert quantitative standard
 pg_cursor.execute("""
 INSERT INTO public.quantitative_standards (
 provision_id, numeric_value, unit, qualifier, 
 context, confidence_score, manual_verified, raw_text
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 """, (
 new_prov_id, numeric_value, unit, qualifier,
 context, confidence or 0.85, verified or False, raw_text
 ))
 
 success_count += 1
 
 if i % 10 == 0:
 print(f"Progress: {i+1}/{len(standards)} - Success: {success_count}, Failed: {failure_count}")
 
 except Exception as e:
 failure_count += 1
 print(f"Error migrating standard {i+1}: {e}")
 continue
 
 # Commit the transaction
 pg_conn.commit()
 
 # Final statistics
 print("\n" + "=" * 50)
 print("QUANTITATIVE STANDARDS MIGRATION COMPLETE")
 print(f"Successful: {success_count}")
 print(f"Failed: {failure_count}")
 print(f"Success Rate: {success_count/(success_count+failure_count)*100:.1f}%")
 
 # Verify the migration
 print("\nVERIFICATION:")
 pg_cursor.execute("SELECT COUNT(*) FROM public.quantitative_standards")
 total_count = pg_cursor.fetchone()[0]
 print(f"Total quantitative standards in PostgreSQL: {total_count}")
 
 pg_cursor.execute("SELECT context, COUNT(*) FROM public.quantitative_standards GROUP BY context ORDER BY count DESC")
 contexts = pg_cursor.fetchall()
 print("Contexts migrated:")
 for context, count in contexts:
 print(f" {context}: {count} standards")
 
 # Close connections
 sqlite_conn.close()
 pg_conn.close()
 
 return success_count > 0

if __name__ == "__main__":
 try:
 success = migrate_quantitative_standards()
 if success:
 print("\nQUANTITATIVE MIGRATION SUCCESSFUL!")
 sys.exit(0)
 else:
 print("\nQUANTITATIVE MIGRATION FAILED!")
 sys.exit(1)
 except Exception as e:
 print(f"\nQUANTITATIVE MIGRATION CRASHED: {e}")
 sys.exit(1)