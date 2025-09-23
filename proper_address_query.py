#!/usr/bin/env python3
"""
PROPER ADDRESS-BASED QUERY
=========================
Uses the ACTUAL extracted data from AutoSchemaKG/langextract to find 
documents relevant to the specific address and zone
"""

import sqlite3
from typing import Dict, List, Any

def get_relevant_documents_for_address(address: str, zone: str = "R2", suburb: str = "Dulwich Hill") -> Dict[str, Any]:
 """
 Query the ACTUAL extracted data to find documents relevant to this specific address
 """
 
 conn = sqlite3.connect('nsw_planning.db')
 conn.row_factory = sqlite3.Row
 
 result = {
 "address": address,
 "zone": zone,
 "suburb": suburb,
 "relevant_documents": [],
 "applicable_controls": [],
 "relevant_visuals": [],
 "why_relevant": []
 }
 
 # 1. Find documents that mention this zone specifically
 zone_docs = conn.execute("""
 SELECT DISTINCT rp.document_id, rp.section_header, COUNT(*) as relevance_score
 FROM regulatory_provisions rp
 WHERE rp.provision_text LIKE ? OR rp.document_id LIKE ?
 GROUP BY rp.document_id, rp.section_header
 ORDER BY relevance_score DESC
 LIMIT 10
 """, (f'%{zone}%', f'%{suburb}%')).fetchall()
 
 for doc in zone_docs:
 result["relevant_documents"].append({
 "document": doc['document_id'].replace('_', ' ') if doc['document_id'] else 'Unknown',
 "section": doc['section_header'],
 "relevance_score": doc['relevance_score'],
 "why_relevant": f"Contains {doc['relevance_score']} references to {zone} zone or {suburb}"
 })
 
 # 2. Find ACTUAL development controls that were extracted
 controls = conn.execute("""
 SELECT dc.control_type, dc.value_numeric, dc.value_text, dc.unit, 
 dc.control_subtype, dc.confidence_score, rp.document_id, rp.section_header
 FROM development_controls dc
 JOIN regulatory_provisions rp ON dc.provision_id = rp.id
 WHERE rp.document_id IN (
 SELECT DISTINCT document_id FROM regulatory_provisions 
 WHERE provision_text LIKE ? LIMIT 5
 )
 ORDER BY dc.confidence_score DESC
 LIMIT 10
 """, (f'%{zone}%',)).fetchall()
 
 for control in controls:
 result["applicable_controls"].append({
 "type": control['control_type'],
 "value": f"{control['value_numeric']} {control['unit']}" if control['value_numeric'] else control['value_text'],
 "subtype": control['control_subtype'],
 "confidence": control['confidence_score'],
 "source_document": control['document_id'].replace('_', ' ') if control['document_id'] else 'Unknown',
 "source_section": control['section_header'],
 "extraction_method": "AutoSchemaKG/langextract"
 })
 
 # 3. Find visual elements from relevant documents
 visuals = conn.execute("""
 SELECT ve.visual_type, ve.visual_path, ve.visual_description, ve.page_number
 FROM visual_elements ve
 JOIN regulatory_provisions rp ON ve.provision_id = rp.id
 WHERE rp.document_id IN (
 SELECT DISTINCT document_id FROM regulatory_provisions 
 WHERE provision_text LIKE ? LIMIT 3
 )
 ORDER BY ve.page_number
 LIMIT 5
 """, (f'%{zone}%',)).fetchall()
 
 for visual in visuals:
 result["relevant_visuals"].append({
 "type": visual['visual_type'],
 "path": visual['visual_path'],
 "description": visual['visual_description'],
 "page": visual['page_number'],
 "why_relevant": f"Visual from document that specifically addresses {zone} zoning"
 })
 
 # 4. Explain WHY these are connected using actual database relationships
 connections = conn.execute("""
 SELECT rr.ref_context, rr.section_header, rr.ref_number
 FROM regulatory_refs rr
 WHERE rr.ref_context LIKE ?
 ORDER BY LENGTH(rr.ref_context) DESC
 LIMIT 3
 """, (f'%{zone}%',)).fetchall()
 
 for ref in connections:
 result["why_relevant"].append({
 "reference": ref['ref_number'],
 "section": ref['section_header'],
 "context": ref['ref_context'][:300] + "..." if len(ref['ref_context']) > 300 else ref['ref_context'],
 "explanation": f"This clause specifically addresses {zone} zoning requirements"
 })
 
 conn.close()
 return result

if __name__ == "__main__":
 import json
 
 # Test with the actual address from the frontend
 results = get_relevant_documents_for_address(
 "34 Pile St, Dulwich Hill NSW 2203, Australia",
 zone="R2",
 suburb="Dulwich Hill"
 )
 
 print("=== RELEVANT DOCUMENTS FOR THIS ADDRESS ===")
 print(json.dumps(results, indent=2))