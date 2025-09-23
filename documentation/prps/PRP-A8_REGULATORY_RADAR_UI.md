# PRP-A8: Regulatory Radar UI with NSW API Integration

## Status: IN PROGRESS
**Started:** 2025-08-29 
**Previous:** PRP-A7 Frontend Integration (COMPLETED) 
**Next:** TBD

## Objective
Transform the existing 2-column web interface into a "Regulatory Radar" that displays property-specific intelligence using NSW Planning APIs and AutoSchemaKG relationship mapping.

## Problem Statement
Current system limitations identified in PRP-A7 testing:
- Returns wrong location data (Marrickville rules for Ashfield addresses)
- Dumps generic information instead of specific answers
- No location-aware filtering or property intelligence
- Missing integration with available NSW Government Planning APIs

## Solution: Regulatory Radar UI Architecture

### Left Column: Property Intelligence Dashboard
**Data Source:** NSW Planning APIs + Property Analysis
**Display:**
```
 PROPERTY INTELLIGENCE
Address: 45 Liverpool Street, Ashfield NSW 2131
PropId: 123456 (NSW Planning Portal)

 PLANNING CONTROLS
• Zone: R2 Low Density Residential
• Max Height: 8.5m (Clause 4.3) 
• Min Lot Size: 450m² (Clause 4.1)
• FSR: 0.5:1 (Clause 4.4)

 OVERLAYS & CONSTRAINTS 
• Heritage: Local Item #143
• Flood Risk: 1:100 year event
• Bus Route: Major Road Frontage

 QUICK METRICS
• Compliant Lot Size: (600m²)
• Available Height: 6.2m remaining
• Development Potential: Medium
```

### Right Column: Connected Requirements (AutoSchemaKG)
**Data Source:** Knowledge Graph Relationships + Targeted Query System
**Display:**
```
 REGULATORY CONNECTIONS

 HEIGHT LIMIT (8.5m) connects to:
├── Boundary Setbacks → 3m minimum
├── Roof Features → Additional 1m allowed 
├── Heritage Requirements → Original roofline preservation
└── Solar Access → Neighbour protection rules

 R2 ZONE connects to: 
├── Permitted Uses → Dwelling houses, dual occupancy
├── Parking Requirements → 1 space per dwelling
├── Landscaping → 25% site coverage minimum
└── Privacy → Window placement restrictions

 HERITAGE OVERLAY connects to:
├── Building Materials → Brick/timber preferred
├── Window Design → Double-hung traditional
├── Additions → Rear location only
└── Tree Preservation → Significant trees protected
```

## Technical Implementation Plan

### Phase 1: NSW API Integration Layer
**Files to create/modify:**
- `services/nsw_planning_api.py` - API client for NSW Planning Portal
- `services/property_intelligence.py` - Property analysis engine
- `api_server.py` - Enhanced with NSW API preprocessing

**Key Functions:**
```python
async def get_property_intelligence(address: str) -> PropertyIntelligence:
 """Get comprehensive property data from NSW APIs"""
 prop_id = await lookup_property_id(address)
 planning_controls = await get_planning_controls(prop_id)
 return PropertyIntelligence(controls=planning_controls, ...)

async def get_connected_requirements(controls: PlanningControls) -> List[Requirement]:
 """Use AutoSchemaKG to find connected regulatory requirements"""
 graph_query = build_autoschema_query(controls)
 return await query_knowledge_graph(graph_query)
```

### Phase 2: Frontend Transformation
**Files to modify:**
- `frontend/index.html` - Transform to Regulatory Radar layout
- Add NSW API integration to query preprocessing
- Replace generic results with property intelligence + connections

**UI Components:**
- Property Intelligence Card (left column)
- Connected Requirements Tree (right column) 
- Visual connection indicators (lines/arrows)
- Expandable requirement details

### Phase 3: AutoSchemaKG Integration
**Files to enhance:**
- Connect existing AutoSchemaKG output to relationship mapping
- Create knowledge graph queries based on NSW API results
- Filter regulatory content by property-specific constraints

## Success Criteria
1. Address lookup returns correct NSW Planning Portal property ID
2. Property intelligence displays accurate height/zone/overlay data
3. Connected requirements show AutoSchemaKG relationships
4. System returns specific answers instead of document dumps
5. Location-aware filtering eliminates wrong jurisdiction results

## Test Cases
**Primary Test:** 45 Liverpool Street, Ashfield NSW 2131
- Expected Zone: R2 Low Density Residential (Inner West LEP 2022)
- Expected Height: 8.5m or similar (not Marrickville DCP rules)
- Expected Connections: Height → Setbacks → Heritage → Materials

**Secondary Tests:**
- 15 Norton Street, Leichhardt NSW 2040
- 67 Marrickville Road, Marrickville NSW 2204

## Dependencies
- NSW Planning Portal APIs (confirmed working in api_keys_reference.md)
- Existing AutoSchemaKG knowledge graph data
- Current LightRAG validated query system
- FastAPI server framework

## Notes
This PRP addresses the core user feedback from PRP-A7:
- "the property is in ashfield... why does it return marrickville rules"
- "why does it dump everything instead of answering height limits"
- Transform from "document search" to "property-specific planning advisor"