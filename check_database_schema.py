#!/usr/bin/env python3
"""
Check database schema and regulatory provisions content for clause text analysis
"""
import psycopg2
from dotenv import load_dotenv
import os

def main():
 load_dotenv()

 try:
 # Connect to database
 conn = psycopg2.connect(
 host='localhost',
 database='nsw_planning',
 user=os.getenv('PGUSER', 'postgres'),
 password=os.getenv('PGPASSWORD', 'password')
 )

 cur = conn.cursor()

 # Get table schema for regulatory_provisions
 print('=== REGULATORY_PROVISIONS TABLE SCHEMA ===')
 cur.execute("""
 SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
 FROM information_schema.columns 
 WHERE table_name = 'regulatory_provisions' 
 ORDER BY ordinal_position;
 """)

 schema_rows = cur.fetchall()
 if not schema_rows:
 print("No regulatory_provisions table found!")
 # Check what tables exist
 cur.execute("""
 SELECT table_name FROM information_schema.tables 
 WHERE table_schema = 'public' 
 ORDER BY table_name;
 """)
 tables = cur.fetchall()
 print("\nAvailable tables:")
 for table in tables:
 print(f" - {table[0]}")
 else:
 print(f"{'Column':<25} | {'Type':<15} | {'Max Len':<10} | {'Nullable':<8} | {'Default'}")
 print("-" * 80)
 for row in schema_rows:
 print(f"{row[0]:<25} | {row[1]:<15} | {str(row[2]) if row[2] else 'N/A':<10} | {row[3]:<8} | {str(row[4]) if row[4] else 'N/A'}")

 print()
 print('=== SAMPLE REGULATORY PROVISIONS DATA ===')
 cur.execute("""
 SELECT id, document_title, provision_type, clause_number, provision_text, page_number
 FROM regulatory_provisions 
 LIMIT 3;
 """)

 sample_rows = cur.fetchall()
 for i, row in enumerate(sample_rows, 1):
 print(f'Sample {i}:')
 print(f' ID: {row[0]}')
 print(f' Document: {row[1]}')
 print(f' Type: {row[2]}')
 print(f' Clause: {row[3]}')
 print(f' Text: {row[4][:200] + "..." if row[4] and len(row[4]) > 200 else row[4]}')
 print(f' Page: {row[5]}')
 print('---')

 conn.close()
 
 except psycopg2.Error as e:
 print(f"Database error: {e}")
 except Exception as e:
 print(f"Error: {e}")

if __name__ == "__main__":
 main()