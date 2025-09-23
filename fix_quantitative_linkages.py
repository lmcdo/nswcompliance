"""
Fix quantitative standards linkages for PRP-K7
Create missing links between provisions and quantitative standards
"""
import sqlite3
import re

def extract_setback_value(text, boundary_type):
 """Extract numeric setback value for a given boundary type"""
 text_lower = text.lower()
 
 # Common patterns for setback values
 patterns = {
 'front': [
 r'front.*?(\d+(?:\.\d+)?)\s*metre',
 r'(\d+(?:\.\d+)?)\s*metre.*?front',
 r'front setback.*?(\d+(?:\.\d+)?)',
 ],
 'side': [
 r'side.*?(\d+(?:\.\d+)?)\s*metre',
 r'(\d+(?:\.\d+)?)\s*metre.*?side',
 r'side setback.*?(\d+(?:\.\d+)?)',
 ],
 'rear': [
 r'rear.*?(\d+(?:\.\d+)?)\s*metre',
 r'(\d+(?:\.\d+)?)\s*metre.*?rear',
 r'rear setback.*?(\d+(?:\.\d+)?)',
 ]
 }
 
 for pattern in patterns.get(boundary_type, []):
 match = re.search(pattern, text_lower)
 if match:
 value = float(match.group(1))
 if 0.5 <= value <= 30: # Reasonable range
 return value
 return None

def fix_quantitative_linkages():
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Find all setback provisions without quantitative standards
 cursor.execute('''
 SELECT id, zone, development_type, provision_text, ref_number
 FROM regulatory_provisions
 WHERE zone IN ('R1', 'R2', 'R3', 'R4')
 AND (section_header LIKE '%setback%' 
 OR provision_text LIKE '%setback%'
 OR provision_text LIKE '%metre%front%'
 OR provision_text LIKE '%metre%side%'
 OR provision_text LIKE '%metre%rear%')
 AND id NOT IN (SELECT DISTINCT provision_id FROM quantitative_standards WHERE context LIKE 'setback%')
 LIMIT 100
 ''')
 
 unlinked_provisions = cursor.fetchall()
 print(f"Found {len(unlinked_provisions)} unlinked setback provisions")
 
 created_links = 0
 
 for prov_id, zone, dev_type, text, ref_num in unlinked_provisions:
 if not text:
 continue
 
 # Try to extract setback values for each boundary type
 for boundary in ['front', 'side', 'rear']:
 value = extract_setback_value(text, boundary)
 if value:
 try:
 cursor.execute('''
 INSERT INTO quantitative_standards 
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, ?, 'm', 'minimum', ?, 0.85)
 ''', (prov_id, value, f'setback_{boundary}'))
 created_links += 1
 print(f" Linked {zone} {dev_type or 'general'} {boundary}: {value}m (provision {prov_id})")
 except sqlite3.IntegrityError:
 pass # Already exists
 
 # Special handling for known patterns
 # C11 provisions (Multi Dwelling Housing)
 cursor.execute('''
 SELECT id, ref_number, provision_text 
 FROM regulatory_provisions
 WHERE ref_number LIKE 'C11%'
 AND id NOT IN (SELECT DISTINCT provision_id FROM quantitative_standards)
 ''')
 
 c11_provisions = cursor.fetchall()
 for prov_id, ref_num, text in c11_provisions:
 if 'C11 i' in ref_num and '6 metre' in text:
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 6.0, 'm', 'minimum', 'setback_front', 0.95)
 ''', (prov_id,))
 created_links += 1
 elif 'C11 ii' in ref_num and '4 metre' in text:
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 4.0, 'm', 'minimum', 'setback_side', 0.95)
 ''', (prov_id,))
 created_links += 1
 elif 'C11 iii' in ref_num and '4 metre' in text:
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 4.0, 'm', 'minimum', 'setback_rear', 0.95)
 ''', (prov_id,))
 created_links += 1
 
 # C12 provisions (Residential Flat Buildings)
 cursor.execute('''
 SELECT id, ref_number, provision_text
 FROM regulatory_provisions
 WHERE ref_number LIKE 'C12%'
 AND id NOT IN (SELECT DISTINCT provision_id FROM quantitative_standards)
 ''')
 
 c12_provisions = cursor.fetchall()
 for prov_id, ref_num, text in c12_provisions:
 if 'C12 i' in ref_num and '9 metre' in text:
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, 9.0, 'm', 'minimum', 'setback_front', 0.95)
 ''', (prov_id,))
 created_links += 1
 elif 'C12' in ref_num:
 # Extract any numeric values for side/rear
 for boundary in ['side', 'rear']:
 value = extract_setback_value(text, boundary)
 if value:
 cursor.execute('''
 INSERT OR IGNORE INTO quantitative_standards
 (provision_id, numeric_value, unit, qualifier, context, confidence_score)
 VALUES (?, ?, 'm', 'minimum', ?, 0.9)
 ''', (prov_id, value, f'setback_{boundary}'))
 created_links += 1
 
 conn.commit()
 
 print(f"\nCreated {created_links} new quantitative standard links")
 
 # Verify the results
 result = cursor.execute('''
 SELECT 
 rp.zone,
 COUNT(DISTINCT rp.development_type) as dev_types,
 COUNT(DISTINCT qs.id) as standards
 FROM regulatory_provisions rp
 JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone IN ('R2', 'R3', 'R4')
 AND qs.context LIKE 'setback%'
 GROUP BY rp.zone
 ''').fetchall()
 
 print("\nVerification - Linked setback standards by zone:")
 for zone, dev_types, standards in result:
 print(f" {zone}: {dev_types} development types, {standards} standards")
 
 # Check total
 total = cursor.execute('''
 SELECT COUNT(*)
 FROM regulatory_provisions rp
 JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone IN ('R2', 'R3', 'R4')
 AND qs.context LIKE 'setback%'
 ''').fetchone()[0]
 
 print(f"\nTotal linked setback standards for R2/R3/R4: {total}")
 
 conn.close()
 
 return created_links

if __name__ == "__main__":
 links = fix_quantitative_linkages()
 print(f"\nFix complete! Created {links} new linkages.")