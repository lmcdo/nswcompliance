#!/usr/bin/env python3
import sys
import os
sys.path.append(os.getcwd())
from inner_west_compliance_engine import InnerWestComplianceEngine
import json

engine = InnerWestComplianceEngine()
# Use R2 zone for the current test property
result = engine.get_reliable_setback_requirements('R2', 'marrickville')

# Convert to API format
setback_results = []
for req in result:
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

print(json.dumps(setback_results))