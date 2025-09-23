#!/usr/bin/env python3

from db_config import get_connection # Unified PostgreSQL connection

def check_database():
 conn = get_connection()
 cur = conn.cursor()
 
 # Check tables
 tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
 print(f"Tables: {[t[0] for t in tables]}")
 
 # Check regulatory_provisions
 try:
 count = cur.execute("SELECT COUNT(*) FROM regulatory_provisions;").fetchone()[0]
 print(f"Regulatory provisions: {count}")
 
 # Check some sample data
 samples = cur.execute("SELECT document_id, section_header, provision_text FROM regulatory_provisions LIMIT 3;").fetchall()
 print("\nSample provisions:")
 for doc, section, text in samples:
 print(f" {doc} / {section}: {text[:100]}...")
 
 except Exception as e:
 print(f"Error checking regulatory_provisions: {e}")
 
 # Check development_controls
 try:
 count = cur.execute("SELECT COUNT(*) FROM development_controls;").fetchone()[0]
 print(f"Development controls: {count}")
 
 # Check setback controls specifically
 setbacks = cur.execute("SELECT COUNT(*) FROM development_controls WHERE control_type = 'setback';").fetchone()[0]
 print(f"Setback controls: {setbacks}")
 
 # Sample setback data
 samples = cur.execute("""
 SELECT dc.control_type, dc.control_subtype, dc.value_text, dc.value_numeric 
 FROM development_controls dc 
 WHERE dc.control_type = 'setback' 
 LIMIT 5
 """).fetchall()
 print("\nSample setbacks:")
 for ctrl_type, subtype, text, numeric in samples:
 print(f" {subtype}: {text} ({numeric})")
 
 except Exception as e:
 print(f"Error checking development_controls: {e}")
 
 conn.close()

if __name__ == "__main__":
 check_database()