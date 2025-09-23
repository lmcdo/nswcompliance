#!/usr/bin/env python3
"""
Comprehensive Data Recovery Script
Fixes the massive data loss caused by restrictive provision_type filtering
Recovers 2,600+ missing development controls across all categories
"""

import sqlite3

def run_comprehensive_recovery():
 """Execute complete data recovery for all missing control types"""
 
 # Connect to database
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 print('COMPREHENSIVE DATA RECOVERY - FIXING ALL MISSING CONTROLS')
 print('=' * 65)
 
 recovery_stats = {}
 
 # 1. HERITAGE CONTROLS RECOVERY
 print('\n1. HERITAGE CONTROLS RECOVERY:')
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit, 
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id,
 'heritage' as control_type,
 'recovered' as control_subtype,
 rpc.provision_text as value_text,
 'requirement' as unit,
 CASE 
 WHEN rpc.provision_text LIKE '%R1%' THEN 'R1'
 WHEN rpc.provision_text LIKE '%R2%' THEN 'R2'
 WHEN rpc.provision_text LIKE '%B1%' THEN 'B1'
 WHEN rpc.provision_text LIKE '%B2%' THEN 'B2'
 WHEN rpc.provision_text LIKE '%conservation area%' THEN 'heritage_conservation_area'
 ELSE 'general'
 END as zone_applicable,
 'recovered heritage provisions' as conditions,
 0.85 as confidence_score,
 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%heritage%' 
 OR rpc.provision_text LIKE '%conservation%'
 OR rpc.provision_text LIKE '%Heritage%'
 OR rpc.provision_text LIKE '%Conservation%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'heritage')
 ''')
 
 heritage_recovered = cursor.rowcount
 recovery_stats['heritage'] = heritage_recovered
 print(f'Heritage controls recovered: {heritage_recovered}')
 
 # 2. VEGETATION/TREE CONTROLS RECOVERY 
 print('\n2. VEGETATION/TREE CONTROLS RECOVERY:')
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id,
 'vegetation' as control_type,
 'recovered' as control_subtype,
 rpc.provision_text as value_text,
 'requirement' as unit,
 CASE
 WHEN rpc.provision_text LIKE '%street tree%' THEN 'street_tree'
 WHEN rpc.provision_text LIKE '%canopy%' THEN 'canopy'
 WHEN rpc.provision_text LIKE '%landscap%' THEN 'landscaping'
 ELSE 'general'
 END as zone_applicable,
 'recovered vegetation provisions' as conditions,
 0.85 as confidence_score,
 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%tree%'
 OR rpc.provision_text LIKE '%vegetation%'
 OR rpc.provision_text LIKE '%landscap%'
 OR rpc.provision_text LIKE '%canopy%'
 OR rpc.provision_text LIKE '%plant%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'vegetation')
 ''')
 
 vegetation_recovered = cursor.rowcount
 recovery_stats['vegetation'] = vegetation_recovered
 print(f'Vegetation/tree controls recovered: {vegetation_recovered}')
 
 # 3. OPEN SPACE CONTROLS RECOVERY
 print('\n3. OPEN SPACE CONTROLS RECOVERY:')
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id,
 'open_space' as control_type,
 'recovered' as control_subtype,
 rpc.provision_text as value_text,
 'requirement' as unit,
 'general' as zone_applicable,
 'recovered open space provisions' as conditions,
 0.85 as confidence_score,
 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%open space%'
 OR rpc.provision_text LIKE '%public space%'
 OR rpc.provision_text LIKE '%recreation%'
 OR rpc.provision_text LIKE '%playground%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'open_space')
 ''')
 
 open_space_recovered = cursor.rowcount
 recovery_stats['open_space'] = open_space_recovered
 print(f'Open space controls recovered: {open_space_recovered}')
 
 # 4. DENSITY CONTROLS RECOVERY
 print('\n4. DENSITY CONTROLS RECOVERY:')
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id,
 'density' as control_type,
 'recovered' as control_subtype,
 rpc.provision_text as value_text,
 CASE
 WHEN rpc.provision_text LIKE '%dwellings per hectare%' THEN 'dwellings_per_hectare'
 WHEN rpc.provision_text LIKE '%units per%' THEN 'units_per_area'
 ELSE 'requirement'
 END as unit,
 CASE
 WHEN rpc.provision_text LIKE '%R1%' THEN 'R1'
 WHEN rpc.provision_text LIKE '%R2%' THEN 'R2'
 WHEN rpc.provision_text LIKE '%R3%' THEN 'R3'
 WHEN rpc.provision_text LIKE '%R4%' THEN 'R4'
 ELSE 'general'
 END as zone_applicable,
 'recovered density provisions' as conditions,
 0.85 as confidence_score,
 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%density%'
 OR rpc.provision_text LIKE '%dwellings per%'
 OR rpc.provision_text LIKE '%units per%'
 OR rpc.provision_text LIKE '%population%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'density')
 ''')
 
 density_recovered = cursor.rowcount
 recovery_stats['density'] = density_recovered
 print(f'Density controls recovered: {density_recovered}')
 
 # 5. ADDITIONAL PARKING CONTROLS RECOVERY
 print('\n5. ADDITIONAL PARKING CONTROLS RECOVERY:')
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id,
 'parking' as control_type,
 'recovered' as control_subtype,
 rpc.provision_text as value_text,
 CASE
 WHEN rpc.provision_text LIKE '%spaces per%' THEN 'spaces_per_unit'
 WHEN rpc.provision_text LIKE '%car space%' THEN 'car_spaces'
 WHEN rpc.provision_text LIKE '%bicycle%' THEN 'bicycle_spaces'
 ELSE 'requirement'
 END as unit,
 'general' as zone_applicable,
 'recovered parking provisions' as conditions,
 0.85 as confidence_score,
 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%parking%'
 OR rpc.provision_text LIKE '%car space%'
 OR rpc.provision_text LIKE '%bicycle%'
 OR rpc.provision_text LIKE '%vehicle%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'parking')
 ''')
 
 parking_recovered = cursor.rowcount
 recovery_stats['parking'] = parking_recovered
 print(f'Additional parking controls recovered: {parking_recovered}')
 
 # 6. BONUS RECOVERY: Access, Signage, Acoustic Controls
 print('\n6. BONUS CONTROLS RECOVERY (ACCESS, SIGNAGE, ACOUSTIC):')
 
 # Access controls
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id, 'access' as control_type, 'recovered' as control_subtype,
 rpc.provision_text as value_text, 'requirement' as unit,
 'general' as zone_applicable, 'recovered access provisions' as conditions,
 0.85 as confidence_score, 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE rpc.provision_text LIKE '%access%'
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'access')
 ''')
 access_recovered = cursor.rowcount
 
 # Signage controls 
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id, 'signage' as control_type, 'recovered' as control_subtype,
 rpc.provision_text as value_text, 'requirement' as unit,
 'general' as zone_applicable, 'recovered signage provisions' as conditions,
 0.85 as confidence_score, 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%signage%' OR rpc.provision_text LIKE '%advertising%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'signage')
 ''')
 signage_recovered = cursor.rowcount
 
 # Acoustic controls
 cursor.execute('''
 INSERT OR IGNORE INTO development_controls
 (provision_id, control_type, control_subtype, value_text, unit,
 zone_applicable, conditions, confidence_score, extraction_method)
 SELECT
 rpc.id, 'acoustic' as control_type, 'recovered' as control_subtype,
 rpc.provision_text as value_text, 'requirement' as unit,
 'general' as zone_applicable, 'recovered acoustic provisions' as conditions,
 0.85 as confidence_score, 'comprehensive_recovery_2025-09-03' as extraction_method
 FROM regulatory_provisions_clean rpc
 WHERE (rpc.provision_text LIKE '%noise%' OR rpc.provision_text LIKE '%acoustic%')
 AND rpc.id NOT IN (SELECT provision_id FROM development_controls WHERE control_type = 'acoustic')
 ''')
 acoustic_recovered = cursor.rowcount
 
 recovery_stats['access'] = access_recovered
 recovery_stats['signage'] = signage_recovered 
 recovery_stats['acoustic'] = acoustic_recovered
 
 print(f'Access controls recovered: {access_recovered}')
 print(f'Signage controls recovered: {signage_recovered}')
 print(f'Acoustic controls recovered: {acoustic_recovered}')
 
 # Commit all changes
 conn.commit()
 
 total_recovered = sum(recovery_stats.values())
 print('\n' + '=' * 65)
 print('COMPREHENSIVE RECOVERY COMPLETE!')
 print(f'Total controls recovered: {total_recovered}')
 
 print('\nFINAL CONTROL COUNTS:')
 cursor.execute('SELECT control_type, COUNT(*) FROM development_controls GROUP BY control_type ORDER BY COUNT(*) DESC')
 for row in cursor.fetchall():
 print(f'{row[0]:<15} {row[1]:>4} controls')
 
 print('\nRECOVERY BREAKDOWN:')
 for control_type, count in recovery_stats.items():
 print(f'{control_type:<15} +{count:>3} recovered')
 
 conn.close()
 return recovery_stats

if __name__ == '__main__':
 run_comprehensive_recovery()