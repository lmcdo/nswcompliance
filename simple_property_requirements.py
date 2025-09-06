#!/usr/bin/env python3
"""
Simple Property-Specific Requirements
====================================
Shows ACTUAL requirements for the specific property instead of database averages
"""

import sqlite3
import json

def get_meaningful_requirements(address="34 Pile St, Dulwich Hill NSW 2203", zone="R2"):
    """Get requirements that actually matter for this specific property"""
    
    conn = sqlite3.connect('nsw_planning.db')
    conn.row_factory = sqlite3.Row
    
    result = {
        "property_context": {
            "address": address,
            "zone": zone,
            "explanation": f"These requirements apply specifically because this property is zoned {zone} (Low Density Residential)"
        },
        "actual_controls": [],
        "why_connected": [],
        "specific_clauses": []
    }
    
    # Find ACTUAL controls that mention this zone specifically
    zone_specific = conn.execute("""
        SELECT dc.control_type, dc.value_numeric, dc.unit, dc.control_subtype,
               rp.provision_text, rp.document_id, rp.section_header
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id = rp.id  
        WHERE rp.provision_text LIKE ?
          AND dc.value_numeric IS NOT NULL
        ORDER BY dc.control_type
        LIMIT 8
    """, (f'%{zone}%',)).fetchall()
    
    for row in zone_specific:
        control_type = row['control_type']
        value = row['value_numeric']
        unit = row['unit'] or 'm'
        
        result["actual_controls"].append({
            "type": control_type,
            "value": f"{value} {unit}",
            "reason": f"Applies to {zone} zoned properties",
            "source": row['document_id'].replace('_', ' ') if row['document_id'] else 'Unknown',
            "section": row['section_header']
        })
    
    # Find why controls are connected (same documents/sections)
    connections = conn.execute("""
        SELECT dc1.control_type as type1, dc2.control_type as type2,
               COUNT(*) as connection_count, rp.section_header
        FROM development_controls dc1
        JOIN development_controls dc2 ON dc1.provision_id = dc2.provision_id
        JOIN regulatory_provisions rp ON dc1.provision_id = rp.id
        WHERE dc1.control_type != dc2.control_type
          AND dc1.control_type IN ('height', 'setback')
          AND dc2.control_type IN ('height', 'setback')
        GROUP BY dc1.control_type, dc2.control_type, rp.section_header
        LIMIT 5
    """).fetchall()
    
    for row in connections:
        result["why_connected"].append({
            "control1": row['type1'],
            "control2": row['type2'], 
            "reason": f"Both {row['type1']} and {row['type2']} are regulated together in {row['section_header']}",
            "connection_strength": f"Found together in {row['connection_count']} provisions"
        })
    
    # Get specific clauses with actual text
    specific_clauses = conn.execute("""
        SELECT rr.ref_number, rr.ref_context, rr.section_header
        FROM regulatory_refs rr
        WHERE rr.ref_context LIKE ?
        LIMIT 5
    """, (f'%{zone}%',)).fetchall()
    
    for row in specific_clauses:
        result["specific_clauses"].append({
            "clause": row['ref_number'],
            "section": row['section_header'],
            "text": row['ref_context'][:200] + "..." if len(row['ref_context']) > 200 else row['ref_context'],
            "relevance": f"Specifically mentions {zone} requirements"
        })
    
    conn.close()
    return result

if __name__ == "__main__":
    requirements = get_meaningful_requirements()
    print("=== PROPERTY-SPECIFIC REQUIREMENTS ===")
    print(json.dumps(requirements, indent=2))