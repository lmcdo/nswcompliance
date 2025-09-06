# PRP-A9: LGA-Filtered Connected Requirements System

## Status: PENDING
**Created:** 2025-08-30  
**Previous:** PRP-A8 Regulatory Radar UI (IN PROGRESS)  
**Next:** TBD

## Objective
Fix the connected requirements system to return property-specific, jurisdiction-aware regulatory relationships instead of cross-council document mixing.

## Problem Statement
**Current Issue Identified:** Mosman property returning Marrickville DCP documents
- Query: "7 Milner St, Mosman NSW 2088, Australia" 
- Expected: Mosman Local Environmental Plan 2012 connected requirements
- **Actual**: "Marrickville DCP 2011 - 2 12 Signs and Advertising Structures" 
- **Root Cause**: No LGA filtering in query system, AutoSchemaKG relations not property-aware

## Data Architecture Analysis

### Layer 1: NSW Planning API (Live Government Data) ✅ WORKING
**Status**: Fixed in address resolution - returns correct LGA
```
Property ID 760605 → Planning Controls:
├── Zone: R2 (Land Zoning Map)  
├── Height: 8.5m (Height of Buildings Map)
├── FSR: 0.5:1 (Floor Space Ratio Map) 
└── LGA: MOSMAN ← KEY FOR FILTERING
```

### Layer 2: Document Knowledge Base (LightRAG) ❌ NOT FILTERED
**Status**: Returns documents from wrong jurisdictions
```
Current Behavior:
Query: "Mosman height limit" → Returns: Marrickville DCP ❌

Required Behavior:  
Query: "Mosman height limit" → Filter: LGA=MOSMAN → Returns: Mosman LEP ✅
```

### Layer 3: AutoSchemaKG Relations ❌ NOT PROPERTY-AWARE  
**Status**: Generic concept mapping without jurisdictional context
```
Current: height_limit → [all height documents across all councils]
Required: height_limit + LGA=MOSMAN → [Mosman-specific height requirements]
```

### Layer 4: Connected Requirements UI ❌ SHOWS WRONG DATA
**Status**: Displays cross-jurisdictional results instead of property-specific connections

## Solution Architecture

### Phase 1: Implement LGA-Filtered Querying (PRIORITY 1)
**Files to modify:**
- Query system endpoint (`/query`) in `api_server.py`
- Add LGA parameter to query preprocessing
- Filter document search by jurisdiction

```python
async def get_connected_requirements(property_data: PropertyIntelligence):
    # Extract jurisdiction context from NSW API
    lga_filter = property_data.lga_name  # "MOSMAN"
    applicable_lep = property_data.applicable_lep  # "Mosman Local Environmental Plan 2012"
    
    # Build jurisdiction-aware query filter
    jurisdiction_filter = f"({lga_filter} OR State Environmental Planning Policy) NOT (Marrickville OR Inner West OR Canterbury)"
    
    # Query with LGA filtering
    query_context = f"{property_data.zone} zone {property_data.height_limit} height limit {lga_filter} connected requirements"
    filtered_results = await query_knowledge_graph(query_context, jurisdiction_filter)
    
    return filtered_results
```

### Phase 2: AutoSchemaKG Contextual Mapping (PRIORITY 2)
**Files to enhance:**
- AutoSchemaKG relationship mapping
- Property-aware concept connections

```python
# Transform from generic to contextual relationships
concept_context = {
    "height_limit": {"value": "8.5m", "clause": "Clause 4.3", "lga": "MOSMAN"},
    "zone": {"type": "R2", "description": "Low Density Residential", "lga": "MOSMAN"}, 
    "property_address": "7 Milner St, Mosman NSW 2088",
    "applicable_lep": "Mosman Local Environmental Plan 2012"
}

# Build contextual connection tree
connected_tree = {
    "HEIGHT_LIMIT_8_5M": {
        "source": "Mosman LEP Clause 4.3",
        "connections": [
            {"concept": "setbacks", "requirement": "3m minimum boundary setback", "source": "Mosman LEP"},
            {"concept": "solar_access", "requirement": "Neighbor shadow protection", "source": "Mosman LEP"},
            {"concept": "building_envelope", "requirement": "Within height plane", "source": "Mosman LEP"}
        ]
    },
    "R2_ZONE": {
        "source": "Mosman LEP Land Zoning Map",
        "connections": [
            {"concept": "parking", "requirement": "1 space per dwelling", "source": "Mosman LEP"},
            {"concept": "landscaping", "requirement": "25% site coverage minimum", "source": "Mosman LEP"},
            {"concept": "permitted_uses", "requirement": "Dwelling house, dual occupancy", "source": "Mosman LEP"}
        ]
    }
}
```

### Phase 3: Hierarchical UI Response Structure (PRIORITY 3)
**Expected UI Output:**
```
🔗 CONNECTED REGULATORY REQUIREMENTS

📏 HEIGHT LIMIT (8.5m) connects to:
├── 📐 Boundary Setbacks → 3m minimum (Mosman LEP Clause X.X)
├── 🏠 Building Envelope → Within height plane (Mosman LEP)  
├── ☀️ Solar Access → Neighbor protection rules (Mosman LEP)
└── 🌳 Tree Protection → Existing tree heights (Mosman LEP)

🏠 R2 ZONE connects to:
├── 🚗 Parking → 1 space per dwelling (Mosman LEP)
├── 🌱 Landscaping → 25% site coverage (Mosman LEP)  
├── 🏡 Permitted Uses → Dwelling house, dual occupancy (Mosman LEP)
└── 🔒 Privacy → Window placement restrictions (Mosman LEP)

🏛️ MOSMAN LEP connects to:
├── 📜 Development Standards → All R2 requirements
├── 🏗️ Development Assessment → DA requirements  
└── 🌍 State Policies → Applicable SEPPs
```

## Implementation Steps

### Step 1: Add LGA Parameter to Query System
```python
# Modify query endpoint to accept LGA filter
@app.post("/query")
async def query_endpoint(
    address: str,
    lga_name: Optional[str] = None,  # NEW PARAMETER
    query_type: str = "all"
):
    if lga_name:
        # Filter documents by jurisdiction
        jurisdiction_query = f"LGA:{lga_name} OR State Environmental Planning Policy"
        # Apply filter to LightRAG/document search
```

### Step 2: Frontend Integration
```javascript
// Modified getConnectedRequirements() function
async function getConnectedRequirements() {
    const propertyData = window.currentPropertyIntelligence; // From NSW API
    
    const response = await fetch('http://localhost:8001/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            address: propertyData.address,
            lga_name: propertyData.lga_name,  // FILTER BY LGA
            query_type: 'connected_requirements',
            context: `${propertyData.zone} zone ${propertyData.height_limit} height connected requirements`
        })
    });
}
```

### Step 3: Document Source Verification
```python
# Filter results to exclude wrong jurisdictions  
def filter_by_jurisdiction(results: List[Document], target_lga: str) -> List[Document]:
    filtered = []
    for doc in results:
        # Only include if document matches target LGA or is state-wide
        if target_lga.upper() in doc.source.upper() or "SEPP" in doc.source.upper():
            filtered.append(doc)
        # Exclude other council documents explicitly  
        elif any(council in doc.source.upper() for council in ["MARRICKVILLE", "INNER WEST", "CANTERBURY"]):
            continue
    return filtered
```

## Success Criteria
1. ✅ Mosman property returns ONLY Mosman LEP + State SEPP documents
2. ✅ No cross-jurisdictional document mixing (no Marrickville DCP for Mosman addresses)
3. ✅ Connected requirements show property-specific relationships  
4. ✅ AutoSchemaKG relations filtered by LGA context
5. ✅ UI displays hierarchical connection tree with sources

## Test Cases
**Primary Test:** 7 Milner St, Mosman NSW 2088, Australia
- Expected Sources: Mosman Local Environmental Plan 2012, applicable SEPPs ONLY
- Forbidden Sources: Marrickville DCP, Inner West DCP, Canterbury LEP
- Expected Connections: Height (8.5m) → Setbacks → Solar access → Building envelope

**Secondary Test:** 34 Pile St, Dulwich Hill NSW 2203, Australia  
- Expected Sources: Inner West LEP/DCP ONLY
- Forbidden Sources: Penrith LEP, Marrickville DCP (if not Inner West jurisdiction)

## Dependencies  
- Fixed NSW API address resolution (✅ COMPLETED in previous session)
- Existing AutoSchemaKG knowledge graph data
- LightRAG document query system
- Property intelligence data structure

## Notes
This PRP directly addresses the core issue identified:
> "Returns wrong location data (Marrickville rules for Ashfield addresses)"

The solution ensures property intelligence (Layer 1) drives filtering for all other data layers (2-4).