#!/usr/bin/env python3
import sqlite3

def check_relationship_data():
 conn = sqlite3.connect('nsw_planning.db')
 conn.row_factory = sqlite3.Row
 
 # Check regulatory_refs with context
 print("=== REGULATORY REFS WITH CONTEXT ===")
 cursor = conn.execute('''
 SELECT ref_type, ref_number, ref_context, section_header 
 FROM regulatory_refs 
 WHERE ref_context IS NOT NULL AND ref_context != '' 
 LIMIT 3
 ''')
 
 for row in cursor:
 print(f"Type: {row['ref_type']}")
 print(f"Number: {row['ref_number']}")
 print(f"Context: {row['ref_context'][:200]}...")
 print(f"Section: {row['section_header']}")
 print("---")
 
 # Check development_controls
 print("\n=== DEVELOPMENT CONTROLS ===")
 cursor = conn.execute('SELECT * FROM development_controls LIMIT 3')
 for row in cursor:
 print(dict(row))
 print("---")
 
 # Check regulatory_provisions 
 print("\n=== REGULATORY PROVISIONS ===")
 cursor = conn.execute('''
 SELECT control_type, control_value, clause_text, document_name
 FROM regulatory_provisions 
 WHERE clause_text IS NOT NULL 
 LIMIT 3
 ''')
 for row in cursor:
 print(f"Control: {row['control_type']} = {row['control_value']}")
 print(f"Clause: {row['clause_text'][:150]}...")
 print(f"Document: {row['document_name']}")
 print("---")

if __name__ == "__main__":
 check_relationship_data()