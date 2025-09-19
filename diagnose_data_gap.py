"""
Diagnose the data gap between SQLite and PostgreSQL
Find exactly what's missing and the simplest way to fix it
"""

import sqlite3
import psycopg2
import psycopg2.extras
from collections import defaultdict

def analyze_databases():
    print("COMPREHENSIVE DATA GAP ANALYSIS")
    print("="*60)
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect('nsw_planning.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    pg_conn = psycopg2.connect(
        host='localhost', port=5432, database='nsw_planning',
        user='postgres', password='postgres',
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    
    print("\nBASIC COUNTS")
    print("-" * 30)
    
    # Basic counts
    sqlite_provisions = sqlite_conn.execute('SELECT COUNT(*) FROM regulatory_provisions').fetchone()[0]
    pg_provisions = pg_conn.cursor()
    pg_provisions.execute('SELECT COUNT(*) FROM regulatory_provisions')
    pg_provision_count = pg_provisions.fetchone()['count']
    
    sqlite_standards = sqlite_conn.execute('SELECT COUNT(*) FROM quantitative_standards').fetchone()[0]
    pg_standards = pg_conn.cursor()
    pg_standards.execute('SELECT COUNT(*) FROM quantitative_standards')
    pg_standard_count = pg_standards.fetchone()['count']
    
    print(f"Provisions: SQLite={sqlite_provisions:,} vs PostgreSQL={pg_provision_count:,}")
    print(f"Standards:  SQLite={sqlite_standards:,} vs PostgreSQL={pg_standard_count:,}")
    
    print("\nZONE ANALYSIS")
    print("-" * 30)
    
    # Zone comparison
    sqlite_zones = sqlite_conn.execute('''
        SELECT zone, COUNT(*) as provisions, 
               COUNT(DISTINCT development_type) as dev_types
        FROM regulatory_provisions 
        WHERE zone IS NOT NULL 
        GROUP BY zone ORDER BY zone
    ''').fetchall()
    
    pg_zones = pg_conn.cursor()
    pg_zones.execute('''
        SELECT zone, COUNT(*) as provisions,
               COUNT(DISTINCT development_type) as dev_types
        FROM regulatory_provisions 
        WHERE zone IS NOT NULL 
        GROUP BY zone ORDER BY zone
    ''')
    pg_zone_data = pg_zones.fetchall()
    
    print("SQLite zones:")
    sqlite_zone_dict = {}
    for row in sqlite_zones:
        zone = row['zone']
        sqlite_zone_dict[zone] = {'provisions': row['provisions'], 'dev_types': row['dev_types']}
        print(f"  {zone}: {row['provisions']} provisions, {row['dev_types']} dev types")
    
    print("\nPostgreSQL zones:")
    pg_zone_dict = {}
    for row in pg_zone_data:
        zone = row['zone']
        pg_zone_dict[zone] = {'provisions': row['provisions'], 'dev_types': row['dev_types']}
        print(f"  {zone}: {row['provisions']} provisions, {row['dev_types']} dev types")
    
    # Find missing zones
    sqlite_zones_set = set(sqlite_zone_dict.keys())
    pg_zones_set = set(pg_zone_dict.keys())
    missing_in_pg = sqlite_zones_set - pg_zones_set
    missing_in_sqlite = pg_zones_set - sqlite_zones_set
    
    print(f"\nMISSING ZONES:")
    print(f"  In PostgreSQL but not SQLite: {missing_in_sqlite}")
    print(f"  In SQLite but not PostgreSQL: {missing_in_pg}")
    
    print("\nQUANTITATIVE STANDARDS LINKAGE")
    print("-" * 40)
    
    # Standards linkage analysis
    sqlite_linked = sqlite_conn.execute('''
        SELECT rp.zone, rp.development_type, COUNT(qs.id) as standards
        FROM regulatory_provisions rp
        JOIN quantitative_standards qs ON rp.id = qs.provision_id
        WHERE rp.zone IS NOT NULL AND qs.context LIKE '%setback%'
        GROUP BY rp.zone, rp.development_type
        ORDER BY rp.zone, rp.development_type
    ''').fetchall()
    
    pg_linked = pg_conn.cursor()
    pg_linked.execute('''
        SELECT rp.zone, rp.development_type, COUNT(qs.id) as standards
        FROM regulatory_provisions rp
        JOIN quantitative_standards qs ON rp.id = qs.provision_id
        WHERE rp.zone IS NOT NULL AND qs.context LIKE '%setback%'
        GROUP BY rp.zone, rp.development_type
        ORDER BY rp.zone, rp.development_type
    ''')
    pg_linked_data = pg_linked.fetchall()
    
    print("SQLite linked standards:")
    sqlite_links = {}
    for row in sqlite_linked:
        key = f"{row['zone']}_{row['development_type']}"
        sqlite_links[key] = row['standards']
        print(f"  {row['zone']} {row['development_type']}: {row['standards']} standards")
    
    print("\nPostgreSQL linked standards:")
    pg_links = {}
    for row in pg_linked_data:
        key = f"{row['zone']}_{row['development_type']}"
        pg_links[key] = row['standards']
        print(f"  {row['zone']} {row['development_type']}: {row['standards']} standards")
    
    print("\nSPECIFIC PROVISION ANALYSIS")
    print("-" * 40)
    
    # Check C11/C12 provisions
    sqlite_c11 = sqlite_conn.execute('''
        SELECT ref_number, zone, development_type, substr(provision_text, 1, 100) as text_sample
        FROM regulatory_provisions 
        WHERE ref_number LIKE 'C11%' OR ref_number LIKE 'C12%'
    ''').fetchall()
    
    pg_c11 = pg_conn.cursor()
    pg_c11.execute('''
        SELECT ref_number, zone, development_type, LEFT(provision_text, 100) as text_sample
        FROM regulatory_provisions 
        WHERE ref_number LIKE 'C11%' OR ref_number LIKE 'C12%'
    ''')
    pg_c11_data = pg_c11.fetchall()
    
    print(f"C11/C12 provisions:")
    print(f"  SQLite: {len(sqlite_c11)} provisions")
    for row in sqlite_c11:
        print(f"    {row['ref_number']}: {row['zone']} {row['development_type']} - {row['text_sample']}...")
    
    print(f"  PostgreSQL: {len(pg_c11_data)} provisions") 
    for row in pg_c11_data:
        print(f"    {row['ref_number']}: {row['zone']} {row['development_type']} - {row['text_sample']}...")
    
    print("\nRECOMMENDATIONS")
    print("-" * 30)
    
    # Generate recommendations
    recommendations = []
    
    if len(missing_in_pg) > 0:
        recommendations.append(f"[MISSING] {len(missing_in_pg)} zones in PostgreSQL: {missing_in_pg}")
        recommendations.append("   -> Need to migrate SQLite zones: " + ", ".join(missing_in_pg))
    
    missing_links = set(sqlite_links.keys()) - set(pg_links.keys())
    if missing_links:
        recommendations.append(f"[MISSING] {len(missing_links)} zone-devtype linkages in PostgreSQL")
        for link in missing_links:
            zone, dev_type = link.split('_', 1)
            count = sqlite_links[link]
            recommendations.append(f"   -> {zone} {dev_type}: need {count} standards")
    
    if len(sqlite_c11) > len(pg_c11_data):
        recommendations.append(f"[MISSING] C11/C12 provisions: SQLite has {len(sqlite_c11)}, PostgreSQL has {len(pg_c11_data)}")
    
    # Print recommendations
    for rec in recommendations:
        print(rec)
    
    # Simple fix strategy
    if recommendations:
        print("\nSIMPLEST FIX STRATEGY:")
        print("1. Copy missing zone provisions from SQLite to PostgreSQL")
        print("2. Copy ALL quantitative_standards with proper provision_id mapping")
        print("3. Update PostgreSQL provision zones where NULL")
        
        return True
    else:
        print("✅ Databases appear to be in sync!")
        return False
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    needs_sync = analyze_databases()
    if needs_sync:
        print("\nReady to create comprehensive sync script...")
    else:
        print("\nNo sync needed!")