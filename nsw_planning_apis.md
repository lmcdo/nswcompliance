# NSW Government Planning APIs - Reference

## API Endpoints

### 1. Address Lookup API
**URL**: `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address`

**Parameters**: 
- `a`: Full address (URL encoded)
- `noOfRecords`: Number of records to return

**Example**: 
```
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=5%20Carlyle%20St%2C%20Wollstonecraft%20NSW%202065%2C%20Australia&noOfRecords=1
```

**Response**:
```json
[
    {
        "address": "5 CARLYLE LANE WOLLSTONECRAFT 2065",
        "propId": 775534,
        "GURASID": 2119354
    }
]
```

### 2. Property Lot Details API
**URL**: `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot`

**Parameters**:
- `propId`: Property ID from address lookup

**Example**:
```
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot?propId=775534
```

**Response**: Returns geometry and lot description (DP numbers, etc.)

### 3. Planning Controls API (CRITICAL for our system)
**URL**: `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect`

**Parameters**:
- `type=property`
- `id`: Property ID 
- `layers=epi`: Environmental Planning Instrument layers

**Example**:
```
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=775534&layers=epi
```

**Critical Response Data for our system**:

#### Height Limits:
```json
{
    "layerName": "Height of Buildings Map",
    "results": [{
        "Maximum Building Height": "8.5",
        "Units": "m",
        "Legislative Clause": "Clause 4.3",
        "EPI Name": "North Sydney Local Environmental Plan 2013",
        "LGA Name": "NORTH SYDNEY"
    }]
}
```

#### Zoning:
```json
{
    "layerName": "Land Zoning Map", 
    "results": [{
        "Zone": "R2",
        "Land Use": "Low Density Residential",
        "EPI Name": "North Sydney Local Environmental Plan 2013",
        "LGA Name": "NORTH SYDNEY"
    }]
}
```

#### Lot Size Requirements:
```json
{
    "layerName": "Lot Size Map",
    "results": [{
        "Lot Size": "450",
        "Units": "m²",
        "Legislative Clause": "Clause 4.1"
    }]
}
```

## Integration Strategy for Our System

### Current Problem:
- Query: "45 Liverpool Street, Ashfield - height limits"
- Returns: Marrickville DCP signage rules (wrong location, wrong content)

### Solution with NSW APIs:
1. **Address Lookup**: Get propId for "45 Liverpool Street, Ashfield"
2. **Planning Controls**: Get actual height limits, zoning, lot size for that specific property
3. **Targeted Query**: Search our knowledge base for relevant provisions ONLY from the correct LEP/DCP

### Expected Improved Result:
Instead of generic document dump, return:
- "Maximum Building Height: 8.5m (Clause 4.3)"
- "Zone: R2 Low Density Residential" 
- "Minimum Lot Size: 450m²"
- "Applicable LEP: Inner West LEP 2022"

## Implementation Priority:
1. Integrate address → propId lookup
2. Integrate propId → planning controls (height, zone, FSR)
3. Filter our knowledge base queries by correct LEP/DCP and zone
4. Return specific numerical limits instead of entire regulatory sections

This will transform our system from "document search" to "property-specific planning advisor".