"""
Fix R4 zone development types for PRP-K7
"""
import sqlite3

def fix_r4_development_types():
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Update R4 provisions that mention RFB or residential flat buildings
 cursor.execute('''
 UPDATE regulatory_provisions
 SET development_type = 'residential_flat_building'
 WHERE zone = 'R4' 
 AND development_type IS NULL
 AND (provision_text LIKE '%residential flat building%' 
 OR provision_text LIKE '%RFB%'
 OR ref_number LIKE 'C12%')
 ''')
 rfb_updated = cursor.rowcount
 print(f"Updated {rfb_updated} R4 provisions to residential_flat_building")
 
 # Update R4 provisions that mention shop top housing
 cursor.execute('''
 UPDATE regulatory_provisions
 SET development_type = 'shop_top_housing'
 WHERE zone = 'R4'
 AND development_type IS NULL
 AND (provision_text LIKE '%shop top%' 
 OR provision_text LIKE '%mixed use%')
 ''')
 shop_updated = cursor.rowcount
 print(f"Updated {shop_updated} R4 provisions to shop_top_housing")
 
 # Set remaining R4 setback provisions to general high-density
 cursor.execute('''
 UPDATE regulatory_provisions
 SET development_type = 'residential_flat_building'
 WHERE zone = 'R4'
 AND development_type IS NULL
 AND section_header LIKE '%setback%'
 ''')
 general_updated = cursor.rowcount
 print(f"Updated {general_updated} remaining R4 setback provisions to RFB")
 
 # Also ensure R2 multi dwelling provisions are properly linked
 cursor.execute('''
 SELECT id, provision_text FROM regulatory_provisions
 WHERE zone = 'R2'
 AND development_type = 'multi_dwelling_housing'
 AND id NOT IN (SELECT provision_id FROM quantitative_standards)
 AND section_header LIKE '%setback%'
 ''')
 unlinked_r2 = cursor.fetchall()
 
 # Create quantitative standards for unlinked R2 provisions
 for prov_id, text in unlinked_r2:
 # Parse setback values from text
 import re
 
 # Look for front setback
 if '6 metre' in text.lower() and 'front' in text.lower():
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards 
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 6.0, 'm', 'minimum', 'setback_front', 0.9)
 ''', (prov_id,))
 
 # Look for side setback 
 if '4 metre' in text.lower() and 'side' in text.lower():
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 4.0, 'm', 'minimum', 'setback_side', 0.9)
 ''', (prov_id,))
 
 # Look for rear setback
 if '4 metre' in text.lower() and 'rear' in text.lower():
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 4.0, 'm', 'minimum', 'setback_rear', 0.9)
 ''', (prov_id,))
 
 links_created = cursor.rowcount
 print(f"Created {links_created} new quantitative standard links for R2")
 
 conn.commit()
 
 # Verify the fixes
 result = cursor.execute('''
 SELECT zone, COUNT(DISTINCT development_type) as dev_types
 FROM regulatory_provisions
 WHERE zone IN ('R2', 'R4')
 AND development_type IS NOT NULL
 GROUP BY zone
 ''').fetchall()
 
 print("\nVerification:")
 for zone, dev_types in result:
 print(f" {zone}: {dev_types} development types")
 
 # Check quantitative standards linkage
 linked = cursor.execute('''
 SELECT COUNT(*)
 FROM regulatory_provisions rp
 JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone IN ('R2', 'R3', 'R4')
 AND qs.context LIKE 'setback%'
 ''').fetchone()[0]
 
 print(f"\nTotal linked setback standards for R2/R3/R4: {linked}")
 
 conn.close()

if __name__ == "__main__":
 fix_r4_development_types()