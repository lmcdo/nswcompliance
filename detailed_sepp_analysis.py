#!/usr/bin/env python3
"""
Detailed analysis of SEPP documents in the source database
"""

import sqlite3
import pandas as pd
import json

def analyze_sepp_provisions():
 """Focus specifically on SEPP provisions and their characteristics"""
 
 conn = sqlite3.connect('nsw_planning.db')
 
 try:
 # Get all SEPP document IDs
 cursor = conn.cursor()
 cursor.execute("SELECT DISTINCT document_id FROM regulatory_provisions WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%' ORDER BY document_id")
 sepp_docs = cursor.fetchall()
 
 print(f"=== SEPP DOCUMENTS FOUND ===")
 print(f"Total SEPP documents: {len(sepp_docs)}")
 
 for doc in sepp_docs:
 print(f" - {doc[0]}")
 
 # Count total SEPP provisions
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'")
 sepp_count = cursor.fetchone()[0]
 print(f"\nTotal SEPP provisions: {sepp_count}")
 
 if sepp_count == 0:
 print("No SEPP provisions found!")
 return
 
 # Get table schema for understanding what data we have
 cursor.execute("PRAGMA table_info(regulatory_provisions)")
 columns = cursor.fetchall()
 col_names = [col[1] for col in columns]
 print(f"\nAvailable columns: {col_names}")
 
 # Analyze SEPP provisions by document
 print(f"\n=== SEPP PROVISIONS BY DOCUMENT ===")
 sepp_filter = "document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'"
 
 for doc in sepp_docs:
 doc_id = doc[0]
 cursor.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE document_id = ?", (doc_id,))
 count = cursor.fetchone()[0]
 print(f"{doc_id}: {count} provisions")
 
 # Check for zone data in SEPP provisions
 print(f"\n=== ZONE DATA IN SEPP PROVISIONS ===")
 
 # Check zone column
 cursor.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE ({sepp_filter}) AND zone IS NOT NULL AND zone != '' AND zone != 'NULL'")
 sepp_with_zones = cursor.fetchone()[0]
 print(f"SEPP provisions with zone data: {sepp_with_zones}")
 
 if sepp_with_zones > 0:
 cursor.execute(f"SELECT DISTINCT zone FROM regulatory_provisions WHERE ({sepp_filter}) AND zone IS NOT NULL AND zone != '' AND zone != 'NULL'")
 zones = cursor.fetchall()
 print(f"Unique zones in SEPP provisions:")
 for zone in zones:
 print(f" - {zone[0]}")
 
 # Check development_type column
 cursor.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE ({sepp_filter}) AND development_type IS NOT NULL AND development_type != '' AND development_type != 'NULL'")
 sepp_with_dev_types = cursor.fetchone()[0]
 print(f"\nSEPP provisions with development_type data: {sepp_with_dev_types}")
 
 if sepp_with_dev_types > 0:
 cursor.execute(f"SELECT DISTINCT development_type FROM regulatory_provisions WHERE ({sepp_filter}) AND development_type IS NOT NULL AND development_type != '' AND development_type != 'NULL'")
 dev_types = cursor.fetchall()
 print(f"Unique development types in SEPP provisions:")
 for dev_type in dev_types:
 print(f" - {dev_type[0]}")
 
 # Sample some SEPP provisions to understand content
 print(f"\n=== SAMPLE SEPP PROVISIONS ===")
 cursor.execute(f"SELECT * FROM regulatory_provisions WHERE ({sepp_filter}) LIMIT 5")
 samples = cursor.fetchall()
 
 for i, sample in enumerate(samples):
 print(f"\nSEPP Sample {i+1}:")
 for j, value in enumerate(sample):
 if value is not None and str(value).strip() and str(value) != 'NULL':
 print(f" {col_names[j]}: {value}")
 
 # Check if these have quantitative data that could affect setbacks
 print(f"\n=== QUANTITATIVE DATA IN SEPP PROVISIONS ===")
 
 # Look for provisions that might contain numeric constraints
 cursor.execute(f"""
 SELECT document_id, provision_text 
 FROM regulatory_provisions 
 WHERE ({sepp_filter}) 
 AND (
 provision_text LIKE '%metre%' OR 
 provision_text LIKE '%meter%' OR 
 provision_text LIKE '%setback%' OR 
 provision_text LIKE '%height%' OR 
 provision_text LIKE '%storey%' OR
 provision_text LIKE '%floor space ratio%' OR
 provision_text LIKE '%FSR%' OR
 provision_text LIKE '%minimum%' OR
 provision_text LIKE '%maximum%'
 )
 LIMIT 10
 """)
 
 quantitative_samples = cursor.fetchall()
 print(f"SEPP provisions with potential quantitative constraints: {len(quantitative_samples)}")
 
 for i, (doc_id, text) in enumerate(quantitative_samples):
 print(f"\nQuantitative Sample {i+1} from {doc_id}:")
 print(f" Text: {text[:200]}...")
 
 # Check for specific SEPP types that commonly override local provisions
 print(f"\n=== SEPP TYPES ANALYSIS ===")
 
 sepp_types = [
 "Housing",
 "Exempt_and_Complying_Development_Codes", 
 "Transport_and_Infrastructure",
 "Resilience_and_Hazards",
 "Primary_Production",
 "Industry_and_Employment",
 "Planning_Systems",
 "Sustainable_Buildings"
 ]
 
 for sepp_type in sepp_types:
 cursor.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%{sepp_type}%'")
 count = cursor.fetchone()[0]
 if count > 0:
 print(f"SEPP ({sepp_type}): {count} provisions")
 
 # Check if this type has zone-specific provisions
 cursor.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%{sepp_type}%' AND zone IS NOT NULL AND zone != '' AND zone != 'NULL'")
 zone_count = cursor.fetchone()[0]
 print(f" - With zones: {zone_count}")
 
 # Check if this type has development type provisions
 cursor.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%{sepp_type}%' AND development_type IS NOT NULL AND development_type != '' AND development_type != 'NULL'")
 dev_type_count = cursor.fetchone()[0]
 print(f" - With development types: {dev_type_count}")
 
 # Export detailed SEPP data for further analysis
 print(f"\n=== EXPORTING SEPP DATA ===")
 
 cursor.execute(f"""
 SELECT document_id, provision_type, ref_number, zone, development_type, provision_text
 FROM regulatory_provisions 
 WHERE ({sepp_filter})
 AND (zone IS NOT NULL OR development_type IS NOT NULL)
 AND (zone != '' OR development_type != '')
 AND (zone != 'NULL' OR development_type != 'NULL')
 """)
 
 sepp_with_targeting = cursor.fetchall()
 
 export_data = []
 for row in sepp_with_targeting:
 export_data.append({
 'document_id': row[0],
 'provision_type': row[1], 
 'ref_number': row[2],
 'zone': row[3],
 'development_type': row[4],
 'provision_text': row[5][:500] if row[5] else None # Truncate for readability
 })
 
 # Save to JSON for review
 with open('sepp_provisions_with_targeting.json', 'w') as f:
 json.dump(export_data, f, indent=2)
 
 print(f"Exported {len(export_data)} SEPP provisions with zone/development type targeting to 'sepp_provisions_with_targeting.json'")
 
 except Exception as e:
 print(f"Error: {e}")
 import traceback
 traceback.print_exc()
 finally:
 conn.close()

if __name__ == "__main__":
 analyze_sepp_provisions()