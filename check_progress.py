#!/usr/bin/env python3
import sqlite3
from datetime import datetime

def check_progress():
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Get total entries
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_refs = cursor.fetchone()[0]
 
 # Get distinct documents processed
 cursor.execute("SELECT DISTINCT document_id FROM regulatory_refs ORDER BY document_id")
 processed_docs = [r[0] for r in cursor.fetchall()]
 
 # Get recent entries (last 100)
 cursor.execute("""
 SELECT document_id, COUNT(*) as entries 
 FROM regulatory_refs 
 GROUP BY document_id 
 ORDER BY COUNT(*) DESC 
 LIMIT 10
 """)
 top_docs = cursor.fetchall()
 
 conn.close()
 
 print(f"DATABASE STATUS - {datetime.now().strftime('%H:%M:%S')}")
 print("=" * 50)
 print(f"Total regulatory references: {total_refs:,}")
 print(f"Documents processed: {len(processed_docs)}")
 print(f"Remaining documents: {127 - len(processed_docs)}")
 
 print("\nTop 10 documents by entries:")
 for doc, count in top_docs:
 print(f" {doc}: {count:,} entries")
 
 print(f"\nCompletion rate: {len(processed_docs)/127*100:.1f}%")

if __name__ == "__main__":
 check_progress()