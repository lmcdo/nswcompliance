#!/usr/bin/env python3
"""Test PRP-8B API with debugging"""

import psycopg2
from services.authoritative_compliance_api import AuthoritativeComplianceAPI

def debug_api():
    # Check what provisions exist
    conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
    cur = conn.cursor()
    
    print("=== AUTHORITATIVE PROVISIONS ===")
    cur.execute('SELECT id, provision_type, applicable_zones, authority_level FROM authoritative.planning_provisions')
    provisions = cur.fetchall()
    for row in provisions:
        print(f'ID: {row[0]}, Type: {row[1]}, Zones: {row[2]}, Authority: {row[3]}')
    
    print(f"\nTotal provisions: {len(provisions)}")
    
    print("\n=== AUTHORITY TIERS ===")
    cur.execute('SELECT provision_id, tier_level, tier_name FROM authoritative.provision_authority_tiers')
    tiers = cur.fetchall()
    for row in tiers:
        print(f'Provision {row[0]}: Tier {row[1]} ({row[2]})')
    
    conn.close()
    
    print("\n=== API TEST ===")
    api = AuthoritativeComplianceAPI()
    result = api.check_compliance(zone_code='R2', development_type='dual_occupancy')
    
    print(f"Tier 1 provisions: {len(result['tier_1_provisions'])}")
    print(f"Tier 2 provisions: {len(result['tier_2_provisions'])}")
    print(f"Primary authorities: {result['primary_authorities']}")
    print(f"Confidence level: {result['confidence_level']}")

if __name__ == "__main__":
    debug_api()