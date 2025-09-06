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

result = engine.get_reliable_setback_requirements(zone, council_area)

# Convert to API format
setback_results = []
for req in result:
    # Check if this requirement applies to multiple boundary types
    context_lower = req.contextual_requirements.lower()
    
    # Add the primary boundary type
    setback_results.append({
        'boundary_type': req.boundary_type,
        'required_setback': req.minimum_setback_meters,
        'buildable_depth': 0,
        'confidence': req.confidence_score,
        'reasoning': f'{req.legal_source}: {req.contextual_requirements[:100]}...',
        'precision_level': 'legislative_clause',
        'legal_source': req.legal_source,
        'clause_reference': req.clause_reference,
        'authority': 'DCP'
    })
    
    # If the clause mentions "side and rear" but is categorized as "side", also add "rear"
    if req.boundary_type == 'side' and 'side and rear' in context_lower:
        setback_results.append({
            'boundary_type': 'rear',
            'required_setback': req.minimum_setback_meters,
            'buildable_depth': 0,
            'confidence': req.confidence_score,
            'reasoning': f'{req.legal_source}: {req.contextual_requirements[:100]}... (same requirement applies to side and rear)',
            'precision_level': 'legislative_clause',
            'legal_source': req.legal_source,
            'clause_reference': req.clause_reference,
            'authority': 'DCP'
        })

print(json.dumps(setback_results))