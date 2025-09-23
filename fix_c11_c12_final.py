"""
Final Fix for C11/C12 Provisions
=================================
Specifically target the C11/C12 provisions that exist but lack proper zone assignments
"""

import psycopg2
import psycopg2.extras
from datetime import datetime

def fix_c11_c12_provisions():
 print("FINAL C11/C12 PROVISION FIX")
 print("="*40)
 
 pg_conn = psycopg2.connect(
 host='localhost', port=5432, database='nsw_planning',
 user='postgres', password='postgres',
 cursor_factory=psycopg2.extras.RealDictCursor
 )
 pg_cursor = pg_conn.cursor()
 
 # Find C11 provisions that mention multi dwelling housing and assign them to R2
 print("1. Fixing C11 Multi Dwelling Housing provisions...")
 pg_cursor.execute('''
 UPDATE regulatory_provisions 
 SET zone = 'R2', development_type = 'multi_dwelling_housing'
 WHERE ref_number LIKE 'C11%'
 AND provision_text ILIKE '%multi dwelling housing%'
 AND zone IS NULL
 ''')
 c11_fixed = pg_cursor.rowcount
 print(f" Fixed {c11_fixed} C11 provisions")
 
 # Find C12 provisions that mention residential flat buildings and assign them to R2
 print("2. Fixing C12 Residential Flat Building provisions...")
 pg_cursor.execute('''
 UPDATE regulatory_provisions
 SET zone = 'R2', development_type = 'residential_flat_building' 
 WHERE ref_number LIKE 'C12%'
 AND (provision_text ILIKE '%residential flat building%' OR provision_text ILIKE '%9 metres%')
 AND zone IS NULL
 ''')
 c12_fixed = pg_cursor.rowcount
 print(f" Fixed {c12_fixed} C12 provisions")
 
 # Create quantitative standards for the newly fixed C11 provisions
 print("3. Creating quantitative standards for C11...")
 
 # Get C11 provisions
 c11_provisions = pg_cursor.execute('''
 SELECT id, ref_number, provision_text
 FROM regulatory_provisions
 WHERE zone = 'R2' 
 AND development_type = 'multi_dwelling_housing'
 AND ref_number LIKE 'C11%'
 ''')
 c11_data = pg_cursor.fetchall()
 
 standards_created = 0
 for prov in c11_data:
 # C11 i: Front setback 6m
 if 'C11 i' in prov['ref_number'] and '6 metre' in prov['provision_text']:
 pg_cursor.execute('''
 INSERT INTO quantitative_standards (
 provision_id, numeric_value, unit, qualifier, context, 
 confidence_score, created_timestamp
 ) VALUES (%s, 6.0, 'm', 'minimum', 'setback_front', 0.95, %s)
 ON CONFLICT DO NOTHING
 ''', (prov['id'], datetime.now()))
 if pg_cursor.rowcount > 0:
 standards_created += 1
 
 # C11 ii: Side setback 4m 
 elif 'C11 ii' in prov['ref_number'] and '4 metre' in prov['provision_text']:
 pg_cursor.execute('''
 INSERT INTO quantitative_standards (
 provision_id, numeric_value, unit, qualifier, context,
 confidence_score, created_timestamp
 ) VALUES (%s, 4.0, 'm', 'minimum', 'setback_side', 0.95, %s)
 ON CONFLICT DO NOTHING 
 ''', (prov['id'], datetime.now()))
 if pg_cursor.rowcount > 0:
 standards_created += 1
 
 # C11 iii: Rear setback 4m
 elif 'C11 iii' in prov['ref_number'] and '4 metre' in prov['provision_text']:
 pg_cursor.execute('''
 INSERT INTO quantitative_standards (
 provision_id, numeric_value, unit, qualifier, context,
 confidence_score, created_timestamp
 ) VALUES (%s, 4.0, 'm', 'minimum', 'setback_rear', 0.95, %s)
 ON CONFLICT DO NOTHING
 ''', (prov['id'], datetime.now()))
 if pg_cursor.rowcount > 0:
 standards_created += 1
 
 print(f" Created {standards_created} quantitative standards for C11")
 
 # Create quantitative standards for C12 provisions
 print("4. Creating quantitative standards for C12...")
 
 c12_provisions = pg_cursor.execute('''
 SELECT id, ref_number, provision_text
 FROM regulatory_provisions 
 WHERE zone = 'R2'
 AND development_type = 'residential_flat_building'
 AND ref_number LIKE 'C12%'
 ''')
 c12_data = pg_cursor.fetchall()
 
 c12_standards = 0
 for prov in c12_data:
 # C12: Front setback 9m
 if '9 metre' in prov['provision_text'] and 'front' in prov['provision_text'].lower():
 pg_cursor.execute('''
 INSERT INTO quantitative_standards (
 provision_id, numeric_value, unit, qualifier, context,
 confidence_score, created_timestamp
 ) VALUES (%s, 9.0, 'm', 'minimum', 'setback_front', 0.95, %s)
 ON CONFLICT DO NOTHING
 ''', (prov['id'], datetime.now()))
 if pg_cursor.rowcount > 0:
 c12_standards += 1
 
 # C12: Side/rear setback 3m
 if '3 metre' in prov['provision_text'] and ('side' in prov['provision_text'].lower() or 'rear' in prov['provision_text'].lower()):
 if 'side' in prov['provision_text'].lower():
 context = 'setback_side'
 else:
 context = 'setback_rear'
 
 pg_cursor.execute('''
 INSERT INTO quantitative_standards (
 provision_id, numeric_value, unit, qualifier, context,
 confidence_score, created_timestamp 
 ) VALUES (%s, 3.0, 'm', 'minimum', %s, 0.95, %s)
 ON CONFLICT DO NOTHING
 ''', (prov['id'], context, datetime.now()))
 if pg_cursor.rowcount > 0:
 c12_standards += 1
 
 print(f" Created {c12_standards} quantitative standards for C12")
 
 pg_conn.commit()
 
 # Final verification
 print("5. Final verification...")
 pg_cursor.execute('''
 SELECT rp.zone, rp.development_type, COUNT(qs.id) as standards
 FROM regulatory_provisions rp
 JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone = 'R2'
 AND qs.context LIKE 'setback_%'
 GROUP BY rp.zone, rp.development_type
 ''')
 
 r2_results = pg_cursor.fetchall()
 print("R2 quantitative standards after fix:")
 for row in r2_results:
 print(f" {row['zone']} {row['development_type']}: {row['standards']} standards")
 
 pg_conn.close()
 
 total_fixed = c11_fixed + c12_fixed
 total_standards = standards_created + c12_standards
 print(f"\nSUCCESS: Fixed {total_fixed} provisions, created {total_standards} standards")
 
 return total_fixed > 0 or total_standards > 0

if __name__ == "__main__":
 success = fix_c11_c12_provisions()
 if success:
 print("\n R2 zone should now have proper setback standards!")
 else:
 print("\n No changes made - provisions may already be fixed")