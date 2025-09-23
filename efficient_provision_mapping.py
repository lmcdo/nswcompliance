#!/usr/bin/env python3
"""
Most Efficient Way to Map Remaining 77% of Provisions
Based on analysis showing document titles contain zone information
"""

import sqlite3
import re
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path

class EfficientProvisionMapper:
 """
 Maps the 17,088 unmapped provisions using document-level patterns
 and hierarchical inference rules
 """
 
 def __init__(self, db_path: str = "nsw_planning.db"):
 self.conn = sqlite3.connect(db_path)
 self.cur = self.conn.cursor()
 
 # Define zone mapping rules based on document patterns
 self.zone_mapping_rules = {
 # Direct zone mentions
 'R1': ['R1', 'General Residential'],
 'R2': ['R2', 'Low Density Residential', '4.1 Low Density'],
 'R3': ['R3', 'Medium Density Residential'],
 'R4': ['R4', 'High Density Residential'],
 'B1': ['B1', 'Neighbourhood Centre', 'Commercial'],
 'B2': ['B2', 'Local Centre'],
 'B3': ['B3', 'Commercial Core'],
 'B4': ['B4', 'Mixed Use'],
 'IN1': ['IN1', 'General Industrial', 'Industrial'],
 'IN2': ['IN2', 'Light Industrial'],
 'SP1': ['SP1', 'Special Activities'],
 'SP2': ['SP2', 'Infrastructure'],
 'RE1': ['RE1', 'Public Recreation'],
 'RE2': ['RE2', 'Private Recreation'],
 'E1': ['E1', 'National Parks'],
 'E2': ['E2', 'Environmental Conservation'],
 'E3': ['E3', 'Environmental Management'],
 'E4': ['E4', 'Environmental Living']
 }
 
 # Chapter to zone mapping (based on DCP structure)
 self.chapter_zone_mapping = {
 '4': 'R2', # Chapter 4 is Low Density Residential
 '4.1': 'R2',
 '4.2': 'R3',
 '4.3': 'R4',
 '5': 'B1', # Chapter 5 is Commercial
 '5.1': 'B1',
 '5.2': 'B2',
 '5.3': 'B4',
 '6': 'IN1', # Chapter 6 is Industrial
 '6.1': 'IN1',
 '6.2': 'IN2'
 }
 
 # Development type inference patterns
 self.dev_type_patterns = {
 'dwelling_house': [
 'dwelling house', 'single dwelling', 'detached house'
 ],
 'dual_occupancy': [
 'dual occupancy', 'duplex', 'two dwellings'
 ],
 'multi_dwelling': [
 'multi dwelling', 'villa', 'townhouse', 'terrace'
 ],
 'apartment': [
 'residential flat', 'apartment', 'unit'
 ],
 'commercial': [
 'shop', 'retail', 'office', 'business'
 ],
 'industrial': [
 'warehouse', 'factory', 'storage', 'industrial'
 ],
 'mixed_use': [
 'mixed use', 'shop top', 'live work'
 ]
 }
 
 def analyze_current_state(self) -> Dict:
 """Analyze current mapping state"""
 
 stats = {}
 
 # Total provisions
 self.cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
 stats['total_provisions'] = self.cur.fetchone()[0]
 
 # Mapped vs unmapped
 self.cur.execute("""
 SELECT 
 SUM(CASE WHEN zone IS NOT NULL THEN 1 ELSE 0 END) as mapped,
 SUM(CASE WHEN zone IS NULL THEN 1 ELSE 0 END) as unmapped
 FROM regulatory_provisions
 """)
 mapped, unmapped = self.cur.fetchone()
 stats['mapped'] = mapped
 stats['unmapped'] = unmapped
 stats['mapping_rate'] = f"{mapped*100//stats['total_provisions']}%"
 
 return stats
 
 def strategy_1_document_title_mapping(self) -> int:
 """
 Map provisions based on document title patterns
 This is the MOST EFFICIENT method
 """
 
 mapped_count = 0
 
 # Get all unmapped provisions with their document info
 self.cur.execute("""
 SELECT rp.id, rp.document_id, d.pdf_name
 FROM regulatory_provisions rp
 JOIN documents d ON rp.document_id = d.id
 WHERE rp.zone IS NULL
 """)
 
 unmapped = self.cur.fetchall()
 
 print(f"\nStrategy 1: Processing {len(unmapped)} unmapped provisions...")
 
 updates = []
 for prov_id, doc_id, pdf_name in unmapped:
 # Try to extract zone from document title
 zone = self.extract_zone_from_title(pdf_name)
 if zone:
 updates.append((zone, prov_id))
 
 # Batch update
 if updates:
 self.cur.executemany(
 "UPDATE regulatory_provisions SET zone = ? WHERE id = ?",
 updates
 )
 self.conn.commit()
 mapped_count = len(updates)
 print(f" [DONE] Mapped {mapped_count} provisions using document titles")
 
 return mapped_count
 
 def strategy_2_inheritance_mapping(self) -> int:
 """
 Inherit zone from other provisions in same document
 Second most efficient method
 """
 
 # Find documents that have both mapped and unmapped provisions
 self.cur.execute("""
 SELECT DISTINCT 
 document_id,
 (SELECT zone FROM regulatory_provisions 
 WHERE document_id = rp.document_id 
 AND zone IS NOT NULL 
 LIMIT 1) as inherited_zone
 FROM regulatory_provisions rp
 WHERE zone IS NULL
 AND EXISTS (
 SELECT 1 FROM regulatory_provisions rp2
 WHERE rp2.document_id = rp.document_id
 AND rp2.zone IS NOT NULL
 )
 """)
 
 inheritance_map = self.cur.fetchall()
 
 mapped_count = 0
 for doc_id, zone in inheritance_map:
 if zone:
 self.cur.execute("""
 UPDATE regulatory_provisions 
 SET zone = ? 
 WHERE document_id = ? AND zone IS NULL
 """, (zone, doc_id))
 
 mapped_count += self.cur.rowcount
 
 self.conn.commit()
 print(f" [DONE] Mapped {mapped_count} provisions using document inheritance")
 
 return mapped_count
 
 def strategy_3_reference_pattern_mapping(self) -> int:
 """
 Map based on reference number patterns (e.g., 4.x = R2, 5.x = B1)
 """
 
 mapped_count = 0
 
 # Get unmapped provisions with reference numbers
 self.cur.execute("""
 SELECT id, ref_number 
 FROM regulatory_provisions 
 WHERE zone IS NULL 
 AND ref_number IS NOT NULL
 """)
 
 updates = []
 for prov_id, ref_num in self.cur.fetchall():
 # Extract chapter from reference
 if ref_num:
 # Try exact chapter match first
 for chapter_key, zone in self.chapter_zone_mapping.items():
 if ref_num.startswith(chapter_key):
 updates.append((zone, prov_id))
 break
 
 if updates:
 self.cur.executemany(
 "UPDATE regulatory_provisions SET zone = ? WHERE id = ?",
 updates
 )
 self.conn.commit()
 mapped_count = len(updates)
 print(f" [DONE] Mapped {mapped_count} provisions using reference patterns")
 
 return mapped_count
 
 def strategy_4_text_content_mapping(self) -> int:
 """
 Use NLP to extract zone mentions from provision text
 Least efficient but catches remaining provisions
 """
 
 # Get unmapped provisions with text
 self.cur.execute("""
 SELECT id, provision_text 
 FROM regulatory_provisions 
 WHERE zone IS NULL 
 AND provision_text IS NOT NULL
 LIMIT 1000
 """)
 
 updates = []
 for prov_id, text in self.cur.fetchall():
 # Look for zone mentions in text
 for zone, patterns in self.zone_mapping_rules.items():
 for pattern in patterns:
 if pattern.lower() in text.lower():
 updates.append((zone, prov_id))
 break
 if updates and updates[-1][1] == prov_id:
 break
 
 if updates:
 self.cur.executemany(
 "UPDATE regulatory_provisions SET zone = ? WHERE id = ?",
 updates
 )
 self.conn.commit()
 print(f" [DONE] Mapped {len(updates)} provisions using text analysis")
 
 return len(updates)
 
 def extract_zone_from_title(self, title: str) -> Optional[str]:
 """Extract zone from document title"""
 
 title_lower = title.lower()
 
 # Check each zone's patterns
 for zone, patterns in self.zone_mapping_rules.items():
 for pattern in patterns:
 if pattern.lower() in title_lower:
 return zone
 
 return None
 
 def add_development_types(self) -> int:
 """
 Map development types based on provision text
 """
 
 mapped_count = 0
 
 # Get provisions without development type
 self.cur.execute("""
 SELECT id, provision_text 
 FROM regulatory_provisions 
 WHERE development_type IS NULL 
 AND provision_text IS NOT NULL
 LIMIT 5000
 """)
 
 updates = []
 for prov_id, text in self.cur.fetchall():
 text_lower = text.lower()
 
 # Check each development type pattern
 for dev_type, patterns in self.dev_type_patterns.items():
 for pattern in patterns:
 if pattern in text_lower:
 updates.append((dev_type, prov_id))
 break
 if updates and updates[-1][1] == prov_id:
 break
 
 if updates:
 self.cur.executemany(
 "UPDATE regulatory_provisions SET development_type = ? WHERE id = ?",
 updates
 )
 self.conn.commit()
 mapped_count = len(updates)
 print(f" [DONE] Mapped {mapped_count} development types")
 
 return mapped_count
 
 def execute_full_mapping(self) -> Dict:
 """
 Execute all mapping strategies in order of efficiency
 """
 
 print("\n" + "="*60)
 print("EFFICIENT PROVISION MAPPING EXECUTION")
 print("="*60)
 
 # Initial state
 initial = self.analyze_current_state()
 print(f"\nInitial State:")
 print(f" Total: {initial['total_provisions']}")
 print(f" Mapped: {initial['mapped']} ({initial['mapping_rate']})")
 print(f" Unmapped: {initial['unmapped']}")
 
 results = {'strategies': {}}
 
 # Execute strategies in order of efficiency
 print("\nExecuting Mapping Strategies:")
 
 # Strategy 1: Document titles (most efficient)
 count1 = self.strategy_1_document_title_mapping()
 results['strategies']['document_title'] = count1
 
 # Strategy 2: Document inheritance
 count2 = self.strategy_2_inheritance_mapping()
 results['strategies']['inheritance'] = count2
 
 # Strategy 3: Reference patterns
 count3 = self.strategy_3_reference_pattern_mapping()
 results['strategies']['reference_pattern'] = count3
 
 # Strategy 4: Text content
 count4 = self.strategy_4_text_content_mapping()
 results['strategies']['text_content'] = count4
 
 # Add development types
 dev_count = self.add_development_types()
 results['development_types_added'] = dev_count
 
 # Final state
 final = self.analyze_current_state()
 results['final_state'] = final
 
 print(f"\n{'='*60}")
 print("MAPPING COMPLETE")
 print(f"{'='*60}")
 print(f"Total Mapped: {count1 + count2 + count3 + count4}")
 print(f"New Mapping Rate: {final['mapping_rate']}")
 print(f"Remaining Unmapped: {final['unmapped']}")
 
 # Save results
 with open('provision_mapping_results.json', 'w') as f:
 json.dump(results, f, indent=2)
 
 return results
 
 def generate_sql_script(self) -> str:
 """
 Generate SQL script for production deployment
 """
 
 script = """
-- Efficient Provision Mapping SQL Script
-- Generated for production deployment

-- Strategy 1: Document Title Mapping
UPDATE regulatory_provisions rp
SET zone = CASE
 WHEN d.pdf_name LIKE '%Low Density%' OR d.pdf_name LIKE '%4.1%' THEN 'R2'
 WHEN d.pdf_name LIKE '%Medium Density%' OR d.pdf_name LIKE '%4.2%' THEN 'R3'
 WHEN d.pdf_name LIKE '%High Density%' OR d.pdf_name LIKE '%4.3%' THEN 'R4'
 WHEN d.pdf_name LIKE '%Commercial%' OR d.pdf_name LIKE '%5.%' THEN 'B1'
 WHEN d.pdf_name LIKE '%Mixed Use%' THEN 'B4'
 WHEN d.pdf_name LIKE '%Industrial%' OR d.pdf_name LIKE '%6.%' THEN 'IN1'
 ELSE zone
END
FROM documents d
WHERE rp.document_id = d.id
AND rp.zone IS NULL;

-- Strategy 2: Document Inheritance
WITH zone_inheritance AS (
 SELECT document_id, MAX(zone) as inherited_zone
 FROM regulatory_provisions
 WHERE zone IS NOT NULL
 GROUP BY document_id
)
UPDATE regulatory_provisions
SET zone = zi.inherited_zone
FROM zone_inheritance zi
WHERE regulatory_provisions.document_id = zi.document_id
AND regulatory_provisions.zone IS NULL;

-- Strategy 3: Reference Pattern Mapping
UPDATE regulatory_provisions
SET zone = CASE
 WHEN ref_number LIKE '4.1%' THEN 'R2'
 WHEN ref_number LIKE '4.2%' THEN 'R3'
 WHEN ref_number LIKE '4.3%' THEN 'R4'
 WHEN ref_number LIKE '5.%' THEN 'B1'
 WHEN ref_number LIKE '6.%' THEN 'IN1'
 ELSE zone
END
WHERE zone IS NULL
AND ref_number IS NOT NULL;
"""
 
 # Save SQL script
 with open('provision_mapping.sql', 'w') as f:
 f.write(script)
 
 print(f"\n[DONE] SQL script saved to provision_mapping.sql")
 
 return script


def main():
 """Main execution"""
 
 mapper = EfficientProvisionMapper()
 
 # Execute full mapping
 results = mapper.execute_full_mapping()
 
 # Generate SQL for production
 mapper.generate_sql_script()
 
 # Print summary
 print("\n" + "="*60)
 print("IMPLEMENTATION SUMMARY")
 print("="*60)
 print("\n1. IMMEDIATE ACTION (1 hour):")
 print(" - Run this script to map ~8,000 provisions")
 print(" - Apply SQL script to production database")
 print("\n2. NEXT STEPS (1 day):")
 print(" - Validate mapped zones with planning team")
 print(" - Add development type inference")
 print(" - Create audit trail for changes")
 print("\n3. LONG TERM (1 week):")
 print(" - Implement ML-based zone extraction")
 print(" - Add SEPP/LEP hierarchy tracking")
 print(" - Build validation interface for planners")


if __name__ == "__main__":
 main()