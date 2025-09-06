#!/usr/bin/env python3
"""
TRACE COMPLIANCE CLAIMS
======================
What exactly is the system claiming and on what basis?
"""

import requests
import json

def trace_compliance_claims():
    # Get the actual API response
    response = requests.post('http://localhost:8006/enhanced-complete-assessment', 
        json={'address': '34 Pile St, Dulwich Hill NSW 2203, Australia', 'query_type': 'complete_assessment'})
    
    data = response.json()
    
    print("=== WHAT THE SYSTEM CLAIMS TO RETURN ===")
    print(f"Success: {data.get('success')}")
    print(f"Assessment type: {data.get('assessment_type')}")
    
    # Property intelligence claims
    prop_intel = data.get('property_intelligence', {})
    if prop_intel:
        context = prop_intel.get('property_context', {})
        print(f"\n--- PROPERTY CLAIMS ---")
        print(f"Zone: {context.get('zone')} (Source: ?)")
        print(f"Height limit: {context.get('height_limit')} metres (Source: ?)")
        print(f"LGA: {context.get('lga_name')} (Source: ?)")
        print(f"LEP: {context.get('applicable_lep')} (Source: ?)")
    
    # Critical controls claims
    critical_controls = prop_intel.get('critical_controls', [])
    if critical_controls:
        print(f"\n--- CRITICAL CONTROLS CLAIMS ---")
        for control in critical_controls:
            print(f"Control: {control.get('control_type')} = {control.get('value')} {control.get('units')}")
            print(f"  Source doc: {control.get('source_document', 'NO SOURCE')}")
            print(f"  Justification: {control.get('justification', 'NO JUSTIFICATION')}")
    
    # Setback calculations claims
    setback_calcs = data.get('setback_calculations', {})
    if setback_calcs:
        print(f"\n--- SETBACK COMPLIANCE CLAIMS ---")
        for setback_type, calc in setback_calcs.items():
            if isinstance(calc, dict):
                print(f"{setback_type}: {calc.get('distance', 'Unknown')}m")
                print(f"  Source: {calc.get('source', 'NO SOURCE')}")
                print(f"  Calculation method: {calc.get('calculation_method', 'NO METHOD')}")
                print(f"  Justification: {calc.get('justification', 'NO JUSTIFICATION')}")
                print(f"  Confidence: {calc.get('confidence_score', 'NO CONFIDENCE')}")
    
    # Connected requirements claims
    connected = data.get('connected_requirements', {})
    if connected:
        print(f"\n--- REGULATORY CONNECTION CLAIMS ---")
        direct = connected.get('direct_connections', [])
        print(f"Claims {len(direct)} direct connections")
        for conn in direct:
            print(f"  {conn.get('control_type')} connected to {conn.get('related_controls')} in {conn.get('document')}")
            print(f"  Basis: {conn.get('type', 'NO BASIS')} (Count: {conn.get('count', 'NO COUNT')})")
    
    print(f"\n=== COMPLIANCE JUSTIFICATION ANALYSIS ===")
    print("Questions that MUST be answered:")
    print("1. WHERE does the height limit '9.5m' come from? Which specific clause?")
    print("2. WHY does this apply to 34 Pile St specifically?")
    print("3. WHAT is the legal basis for setback calculations?")
    print("4. HOW were the 'connected requirements' determined?")
    print("5. WHAT happens if these values are wrong?")
    
    # Check what actual database evidence exists
    print(f"\n=== ACTUAL DATABASE EVIDENCE ===")
    import sqlite3
    conn = sqlite3.connect('nsw_planning.db')
    
    # Find evidence for this specific property
    address_refs = conn.execute("""
        SELECT COUNT(*) as count FROM regulatory_provisions 
        WHERE provision_text LIKE '%Pile%' OR provision_text LIKE '%Dulwich%'
    """).fetchone()[0]
    print(f"Direct references to this address/suburb in database: {address_refs}")
    
    # Find evidence for height limits
    height_evidence = conn.execute("""
        SELECT COUNT(*) as count FROM development_controls 
        WHERE control_type = 'height' AND value_numeric = 9.5
    """).fetchone()[0]
    print(f"Database entries with exactly 9.5m height limit: {height_evidence}")
    
    # Find evidence for zone R2
    r2_evidence = conn.execute("""
        SELECT COUNT(*) as count FROM regulatory_provisions 
        WHERE provision_text LIKE '%R2%'
    """).fetchone()[0]
    print(f"Database entries mentioning R2 zone: {r2_evidence}")
    
    conn.close()

if __name__ == "__main__":
    trace_compliance_claims()