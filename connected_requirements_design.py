#!/usr/bin/env python3
"""
CONNECTED REQUIREMENTS BUTTON - OPTIMAL DESIGN
==============================================

Based on our enhanced database with 22,092 regulatory provisions,
this designs the optimal "Connected Requirements" functionality.

CORE VALUE PROPOSITION:
"Don't just get setbacks - get ALL requirements that affect your development"
"""

import sqlite3
from typing import Dict, List, Any
import json

class ConnectedRequirementsEngine:
 """
 Finds all related requirements for a property beyond just setbacks
 """
 
 def __init__(self, db_path='nsw_planning.db'):
 self.db_path = db_path
 
 def find_connected_requirements(self, property_data, primary_results) -> Dict[str, Any]:
 """
 OPTIMAL ALGORITHM: Multi-layer requirement discovery
 
 Layer 1: Same document sections (direct connections)
 Layer 2: Cross-referenced sections (regulatory links) 
 Layer 3: Same zone requirements (contextual relevance)
 Layer 4: Same development type (practical relevance)
 """
 
 conn = sqlite3.connect(self.db_path)
 cur = conn.cursor()
 
 connected_reqs = {
 "direct_connections": [], # Same document/section
 "regulatory_links": [], # Cross-referenced clauses 
 "zone_requirements": [], # Same zone (R2) requirements
 "development_context": [], # Related to development type
 "compliance_checklist": [] # Complete requirements list
 }
 
 # LAYER 1: Direct Connections - Same Document Sections
 # Find other requirements in same DCP sections that had setbacks
 setback_documents = cur.execute("""
 SELECT DISTINCT rp.document_id, rp.section_header
 FROM regulatory_provisions rp
 JOIN development_controls dc ON rp.id = dc.provision_id
 WHERE dc.control_type = 'setback'
 AND rp.document_id LIKE '%Marrickville%'
 """).fetchall()
 
 for doc, section in setback_documents:
 # Find other controls in same sections
 related_controls = cur.execute("""
 SELECT DISTINCT dc.control_type, dc.control_subtype, 
 COUNT(*) as count, GROUP_CONCAT(DISTINCT dc.value_text, '; ') as values
 FROM development_controls dc
 JOIN regulatory_provisions rp ON dc.provision_id = rp.id 
 WHERE rp.document_id = ? AND rp.section_header = ?
 AND dc.control_type != 'setback'
 GROUP BY dc.control_type, dc.control_subtype
 """, (doc, section)).fetchall()
 
 for control_type, subtype, count, values in related_controls:
 connected_reqs["direct_connections"].append({
 "type": "same_section",
 "control_type": control_type,
 "control_subtype": subtype,
 "document": doc,
 "section": section,
 "count": count,
 "sample_values": values[:100] + "..." if values and len(values) > 100 else values
 })
 
 # LAYER 2: Regulatory Links - Cross-Referenced Clauses
 # Find provisions that reference other sections
 cross_refs = cur.execute("""
 SELECT provision_text, ref_number, section_header, document_id
 FROM regulatory_provisions
 WHERE (provision_text LIKE '%accordance with%' 
 OR provision_text LIKE '%refer to Section%'
 OR provision_text LIKE '%see clause%'
 OR provision_text LIKE '%subject to%')
 AND document_id LIKE '%Marrickville%'
 LIMIT 10
 """).fetchall()
 
 for text, ref, section, doc in cross_refs:
 connected_reqs["regulatory_links"].append({
 "type": "cross_reference", 
 "reference": ref,
 "section": section,
 "document": doc,
 "connection_text": text[:150] + "..." if len(text) > 150 else text
 })
 
 # LAYER 3: Zone Requirements - All R2 Controls
 zone_requirements = cur.execute("""
 SELECT dc.control_type, dc.control_subtype, 
 COUNT(*) as count, AVG(dc.value_numeric) as avg_value,
 GROUP_CONCAT(DISTINCT dc.unit) as units
 FROM development_controls dc
 JOIN regulatory_provisions rp ON dc.provision_id = rp.id
 WHERE rp.zone = ? OR dc.zone_applicable = ?
 GROUP BY dc.control_type, dc.control_subtype
 ORDER BY count DESC
 """, (property_data.zone, property_data.zone)).fetchall()
 
 for control_type, subtype, count, avg_val, units in zone_requirements:
 connected_reqs["zone_requirements"].append({
 "type": "zone_control",
 "control_type": control_type,
 "control_subtype": subtype or "general",
 "zone": property_data.zone,
 "count": count,
 "average_value": f"{avg_val:.1f}" if avg_val else None,
 "units": units
 })
 
 # LAYER 4: Development Context - Related Requirements
 # Find requirements that commonly apply together with setbacks
 common_requirements = [
 "height", "parking", "landscaping", "fsr", "heritage", 
 "stormwater", "amenity", "privacy", "solar access"
 ]
 
 for req_type in common_requirements:
 context_controls = cur.execute("""
 SELECT COUNT(*) as count, 
 GROUP_CONCAT(DISTINCT rp.section_header, '; ') as sections
 FROM regulatory_provisions rp
 WHERE rp.provision_text LIKE ? 
 AND rp.document_id LIKE '%Marrickville%'
 AND LENGTH(rp.provision_text) > 50
 """, (f'%{req_type}%',)).fetchone()
 
 if context_controls[0] > 0:
 connected_reqs["development_context"].append({
 "type": "contextual_requirement",
 "requirement_type": req_type,
 "count": context_controls[0],
 "sections": context_controls[1][:200] + "..." if context_controls[1] and len(context_controls[1]) > 200 else context_controls[1]
 })
 
 # LAYER 5: Compliance Checklist - Complete Requirements
 checklist_items = [
 {"category": "Building Envelope", "items": ["Setbacks", "Height limits", "Building coverage", "Floor space ratio"]},
 {"category": "Site Planning", "items": ["Parking provision", "Landscaping", "Private open space", "Waste management"]}, 
 {"category": "Heritage & Character", "items": ["Heritage conservation", "Streetscape compatibility", "Building design"]},
 {"category": "Environmental", "items": ["Stormwater management", "Solar access", "Privacy protection", "Noise mitigation"]},
 {"category": "Infrastructure", "items": ["Utility services", "Traffic impact", "Construction management"]}
 ]
 
 # Check which checklist items we have data for
 for category_info in checklist_items:
 category = category_info["category"]
 items = category_info["items"]
 
 found_items = []
 for item in items:
 # Check if we have provisions mentioning this requirement
 count = cur.execute("""
 SELECT COUNT(*) FROM regulatory_provisions 
 WHERE provision_text LIKE ? AND document_id LIKE '%Marrickville%'
 """, (f'%{item.lower()}%',)).fetchone()[0]
 
 if count > 0:
 found_items.append({"item": item, "provision_count": count})
 
 if found_items:
 connected_reqs["compliance_checklist"].append({
 "category": category,
 "requirements": found_items
 })
 
 conn.close()
 return connected_reqs
 
 def format_connected_requirements_response(self, connected_reqs: Dict[str, Any]) -> Dict[str, Any]:
 """Format for optimal user experience"""
 
 response = {
 "success": True,
 "connected_requirements": {
 "summary": {
 "total_connections": sum([
 len(connected_reqs["direct_connections"]),
 len(connected_reqs["regulatory_links"]), 
 len(connected_reqs["zone_requirements"]),
 len(connected_reqs["development_context"])
 ]),
 "checklist_categories": len(connected_reqs["compliance_checklist"])
 },
 "priority_connections": {
 "same_section_requirements": connected_reqs["direct_connections"][:5],
 "regulatory_cross_references": connected_reqs["regulatory_links"][:3],
 "zone_specific_controls": connected_reqs["zone_requirements"][:8]
 },
 "development_context": connected_reqs["development_context"],
 "compliance_checklist": connected_reqs["compliance_checklist"],
 "user_actions": [
 {
 "action": "View Heritage Requirements", 
 "description": "Check if heritage controls apply to your property",
 "priority": "HIGH" if any("heritage" in item["requirement_type"].lower() for item in connected_reqs["development_context"]) else "MEDIUM"
 },
 {
 "action": "Calculate Parking Requirements",
 "description": "Determine parking spaces needed for your development", 
 "priority": "HIGH"
 },
 {
 "action": "Review Height Limits",
 "description": "Confirm building height restrictions",
 "priority": "HIGH" 
 },
 {
 "action": "Check FSR Requirements",
 "description": "Verify floor space ratio compliance",
 "priority": "MEDIUM"
 }
 ]
 }
 }
 
 return response

def demonstrate_connected_requirements():
 """Demonstrate the connected requirements functionality"""
 
 print("CONNECTED REQUIREMENTS DEMONSTRATION")
 print("=" * 60)
 
 # Mock property data
 class PropertyData:
 def __init__(self):
 self.address = "123 Smith Street, Marrickville"
 self.zone = "R2"
 self.lga_name = "Inner West"
 
 # Mock primary setback results
 primary_results = {
 "front_setback": "6.0m",
 "side_setback": "1.4m", 
 "rear_setback": "6.0m"
 }
 
 property_data = PropertyData()
 engine = ConnectedRequirementsEngine()
 
 print(f"Property: {property_data.address} ({property_data.zone} zone)")
 print(f"Primary Results: Front {primary_results['front_setback']}, Side {primary_results['side_setback']}, Rear {primary_results['rear_setback']}")
 print()
 
 # Find connected requirements
 print("Finding connected requirements...")
 connected = engine.find_connected_requirements(property_data, primary_results)
 
 # Format response
 response = engine.format_connected_requirements_response(connected)
 
 print()
 print("CONNECTED REQUIREMENTS RESULTS:")
 print("-" * 40)
 
 summary = response["connected_requirements"]["summary"]
 print(f"Total connections found: {summary['total_connections']}")
 print(f"Compliance categories: {summary['checklist_categories']}")
 print()
 
 print("PRIORITY CONNECTIONS:")
 priority = response["connected_requirements"]["priority_connections"]
 
 print(f"Same section requirements: {len(priority['same_section_requirements'])}")
 for req in priority["same_section_requirements"][:3]:
 print(f" - {req['control_type']} ({req.get('control_subtype', 'general')}): {req['count']} controls")
 
 print(f"Zone-specific controls: {len(priority['zone_specific_controls'])}")
 for req in priority["zone_specific_controls"][:3]:
 print(f" - {req['control_type']}: {req['count']} controls in {req['zone']} zone")
 
 print()
 print("USER ACTIONS RECOMMENDED:")
 for action in response["connected_requirements"]["user_actions"]:
 print(f" [{action['priority']}] {action['action']}")
 print(f" {action['description']}")
 
 print()
 print("OPTIMAL BUTTON BEHAVIOR:")
 print("1. Show immediate priority connections (same sections)")
 print("2. Provide actionable next steps (check heritage, parking, etc.)")
 print("3. Complete compliance checklist for professional users")
 print("4. Page citations for council submission")

if __name__ == "__main__":
 demonstrate_connected_requirements()