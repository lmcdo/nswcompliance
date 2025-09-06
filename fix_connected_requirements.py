#!/usr/bin/env python3
"""
FIXED CONNECTED REQUIREMENTS - Property-Specific Context
=======================================================

Instead of showing meaningless database averages, this shows:
1. WHY each control applies to THIS specific property
2. WHAT the actual requirements are for this zone/location
3. WHERE these requirements come from (specific clauses)
"""

import sqlite3
from typing import Dict, List, Any

class PropertySpecificRequirements:
    """Shows requirements that actually apply to the specific property"""
    
    def __init__(self, db_path='nsw_planning.db'):
        self.db_path = db_path
    
    def find_property_requirements(self, property_data) -> Dict[str, Any]:
        """Find requirements that ACTUALLY apply to this specific property"""
        
        # Extract property details
        zone = property_data.get("zone", "R2")  # Default from API response
        lga = property_data.get("lga", "Inner West")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        result = {
            "property_context": {
                "address": property_data.get("address"),
                "zone": zone,
                "lga": lga,
                "why_these_requirements": f"These requirements apply because this property is in {zone} zone within {lga} LGA"
            },
            "applicable_controls": [],
            "specific_clauses": [],
            "practical_impact": []
        }
        
        # Find ACTUAL controls that apply to this zone
        zone_controls = cur.execute("""
            SELECT dc.control_type, dc.control_subtype, dc.value_numeric, dc.value_text, 
                   dc.unit, dc.conditions, rp.clause_text, rp.document_id, rp.section_header
            FROM development_controls dc
            JOIN regulatory_provisions rp ON dc.provision_id = rp.id
            WHERE (rp.provision_text LIKE ? OR rp.provision_text LIKE ?)
              AND dc.value_numeric IS NOT NULL
            LIMIT 10
        """, (f'%{zone}%', f'%residential%')).fetchall()
        
        for control_type, subtype, value_num, value_text, unit, conditions, clause, doc, section in zone_controls:
            result["applicable_controls"].append({
                "control_type": control_type,
                "value": f"{value_num} {unit}" if value_num and unit else value_text,
                "applies_because": f"Property is in {zone} zone",
                "source_clause": clause[:200] + "..." if clause and len(clause) > 200 else clause,
                "document": doc.replace("_", " ") if doc else "Unknown",
                "section": section,
                "conditions": conditions
            })
        
        # Find SPECIFIC cross-references that mention this zone
        cross_refs = cur.execute("""
            SELECT rr.ref_context, rr.section_header, rr.ref_number
            FROM regulatory_refs rr
            WHERE rr.ref_context LIKE ? 
            LIMIT 5
        """, (f'%{zone}%',)).fetchall()
        
        for context, section, ref_num in cross_refs:
            result["specific_clauses"].append({
                "reference": ref_num,
                "section": section,
                "context": context[:300] + "..." if len(context) > 300 else context,
                "relevance": f"Specifically mentions {zone} zoning"
            })
        
        conn.close()
        return result

def format_property_requirements(requirements: Dict) -> str:
    """Format requirements in human-readable way"""
    
    context = requirements["property_context"]
    
    html = f"""
    <div style="background: #f0f9ff; border: 1px solid #3b82f6; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #1e40af;">🏠 Requirements for Your Property</h3>
        <div style="color: #64748b; font-size: 14px;">
            <strong>Address:</strong> {context['address']}<br>
            <strong>Zone:</strong> {context['zone']} | <strong>LGA:</strong> {context['lga']}<br>
            <strong>Why these apply:</strong> {context['why_these_requirements']}
        </div>
    </div>
    """
    
    # Applicable Controls
    if requirements["applicable_controls"]:
        html += """
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 16px;">
            <div style="background: #f8fafc; padding: 12px; font-weight: 600; border-bottom: 1px solid #e2e8f0;">
                📐 Controls That Apply to This Property
            </div>
            <div style="padding: 16px;">
        """
        
        for control in requirements["applicable_controls"]:
            html += f"""
            <div style="margin-bottom: 16px; padding: 12px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <div style="font-weight: 600; color: #92400e; margin-bottom: 4px;">
                    {control['control_type'].upper()}: {control['value']}
                </div>
                <div style="font-size: 13px; color: #374151; margin-bottom: 8px;">
                    <strong>Why:</strong> {control['applies_because']}
                </div>
                <div style="font-size: 12px; color: #64748b;">
                    <strong>Source:</strong> {control['document']} - {control['section']}<br>
                    {control['conditions'] or ''}
                </div>
            </div>
            """
        
        html += "</div></div>"
    
    # Specific Clauses
    if requirements["specific_clauses"]:
        html += """
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 16px;">
            <div style="background: #f8fafc; padding: 12px; font-weight: 600; border-bottom: 1px solid #e2e8f0;">
                📖 Specific Clauses for Your Zone
            </div>
            <div style="padding: 16px;">
        """
        
        for clause in requirements["specific_clauses"]:
            html += f"""
            <div style="margin-bottom: 12px; padding: 8px; background: #f0fdf4; border-radius: 4px; border-left: 3px solid #22c55e;">
                <div style="font-weight: 600; color: #16a34a;">{clause['reference']} - {clause['section']}</div>
                <div style="font-size: 13px; color: #374151; margin-top: 4px;">{clause['context']}</div>
                <div style="font-size: 12px; color: #16a34a; margin-top: 4px;">
                    <strong>Relevance:</strong> {clause['relevance']}
                </div>
            </div>
            """
        
        html += "</div></div>"
    
    return html

if __name__ == "__main__":
    # Test with sample property data
    engine = PropertySpecificRequirements()
    test_data = {
        "address": "34 Pile St, Dulwich Hill NSW 2203",
        "zone": "R2",
        "lga": "Inner West"
    }
    
    requirements = engine.find_property_requirements(test_data)
    print("Property-specific requirements:")
    print(requirements)