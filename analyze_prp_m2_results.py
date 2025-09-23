#!/usr/bin/env python3
"""
Analyze PRP-M2 extraction results
"""

from db_config import get_connection

def analyze_extraction():
 conn = get_connection()
 cursor = conn.cursor()

 print('=== PRP-M2 EXTRACTION ANALYSIS ===')

 # Sample SEPP provisions
 cursor.execute('SELECT sepp_type, provision_category, COUNT(*) FROM sepp_provisions GROUP BY sepp_type, provision_category ORDER BY COUNT(*) DESC')
 sepp_breakdown = cursor.fetchall()
 print('\nSEPP Provisions by Type:')
 for row in sepp_breakdown:
 print(f' {row[0]} - {row[1]}: {row[2]} provisions')

 # Sample LEP provisions
 cursor.execute('SELECT lep_name, lep_zone, COUNT(*) FROM lep_provisions GROUP BY lep_name, lep_zone ORDER BY COUNT(*) DESC LIMIT 10')
 lep_breakdown = cursor.fetchall()
 print('\nTop LEP Provisions by Zone:')
 for row in lep_breakdown:
 print(f' {row[0]} - {row[1]}: {row[2]} provisions')

 # Check what zones we have
 cursor.execute('SELECT DISTINCT lep_zone FROM lep_provisions WHERE lep_zone IS NOT NULL AND lep_zone != \'\' ORDER BY lep_zone')
 zones = [row[0] for row in cursor.fetchall()]
 print(f'\nZones found: {len(zones)}')
 print(f'Sample zones: {zones[:10]}')

 # Sample actual provision text
 cursor.execute('SELECT provision_text FROM sepp_provisions WHERE provision_category = \'exempt\' LIMIT 3')
 exempt_samples = cursor.fetchall()
 print('\nSample SEPP Exempt Provisions:')
 for i, row in enumerate(exempt_samples, 1):
 text = row[0][:100] + '...' if len(row[0]) > 100 else row[0]
 print(f' {i}. {text}')

 conn.close()

if __name__ == "__main__":
 analyze_extraction()