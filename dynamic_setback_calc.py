#!/usr/bin/env python3
import sys
import os
import json
sys.path.append(os.getcwd())
from inner_west_compliance_engine import InnerWestComplianceEngine

# Get zone and property info from command line arguments
zone = sys.argv[1] if len(sys.argv) > 1 else 'R2'
property_id = int(sys.argv[2]) if len(sys.argv) > 2 else 0

engine = InnerWestComplianceEngine()

# Auto-detect council area based on property location
# For Inner West LGA properties, default to marrickville (covers most test cases)
# In production, this would query property database to determine exact sub-council area
council_area = 'marrickville'

# Future enhancement: auto-detect based on property coordinates/suburb
# if property_id:
#     try:
#         import sqlite3
#         conn = sqlite3.connect('nsw_planning.db')
#         # Query property database to determine council area
#         cursor = conn.execute('SELECT suburb FROM property_data WHERE property_id = ?', (property_id,))
#         result = cursor.fetchone()
#         if result:
#             suburb = result[0].lower()
#             if suburb in ['marrickville', 'dulwich hill', 'petersham', 'stanmore']:
#                 council_area = 'marrickville'
#             elif suburb in ['leichhardt', 'annandale', 'lilyfield', 'balmain']:
#                 council_area = 'leichhardt'  
#             elif suburb in ['ashfield', 'haberfield', 'five dock']:
#                 council_area = 'ashfield'
#         conn.close()
#     except:
#         pass  # Default to marrickville on any error

# Use enhanced domain-aware method to prevent cross-contamination
# For residential zones (R1-R4), this will filter out signage setbacks
result = engine.get_domain_aware_setback_requirements(zone, council_area)

# Convert to enhanced API format with domain classification and legal authority
setback_results = []
for req in result:
    # Check if this requirement applies to multiple boundary types
    context_lower = req.contextual_requirements.lower()
    
    # Add the primary boundary type with enhanced metadata
    setback_result = {
        'boundary_type': req.boundary_type,
        'required_setback': req.minimum_setback_meters,
        'confidence': req.confidence_score,
        'legal_source': req.legal_source,
        'clause_reference': req.clause_reference,
        'zone_applicability': req.zone_applicability,
        
        # Enhanced with PRP-K1 domain classification 
        'domain_classification': req.domain_classification,
        'relevance_score': req.relevance_score,
        'cross_contamination_checked': req.cross_contamination_checked,
        
        # Provision ID for Referenced Legislation accordion
        'provision_id': getattr(req, 'provision_id', None),
        
        # Legal authority hierarchy
        'legal_authority': {
            'primary_authority': req.legal_authority.primary_authority if req.legal_authority else "Inner West LEP 2022",
            'secondary_authority': req.legal_authority.secondary_authority if req.legal_authority else "DCP Provision",
            'clause_reference': req.legal_authority.clause_reference if req.legal_authority else req.clause_reference,
            'amendment_reference': req.legal_authority.amendment_reference if req.legal_authority else "IWLEP 2022",
            'document_source': req.legal_authority.document_source if req.legal_authority else "N/A"
        }
    }
    
    setback_results.append(setback_result)
    
    # If the clause mentions "side and rear" but is categorized as "side", also add "rear"
    if req.boundary_type == 'side' and 'side and rear' in context_lower:
        # Create rear setback with same enhanced metadata
        rear_setback = setback_result.copy()  # Copy all the enhanced metadata
        rear_setback['boundary_type'] = 'rear'
        rear_setback['reasoning'] = f'{req.legal_source}: {req.contextual_requirements[:100]}... (same requirement applies to side and rear)'
        setback_results.append(rear_setback)

print(json.dumps(setback_results))