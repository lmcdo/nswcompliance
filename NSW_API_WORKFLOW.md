# NSW Planning API - Complete Workflow

## Three Required API Calls for Full Planning Data

### 1. Address Lookup
```
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=34%20Pile%20St%2C%20Dulwich%20Hill%20NSW%202203%2C%20Australia&noOfRecords=1
```
**Returns:** `propId` and `GURASID`

### 2. Lot Details  
```
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot?propId=1922183
```
**Returns:** Lot information and geometry

### 3. Layer Intersect (THE MONEY SHOT)
```
https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=1922183&layers=epi
```
**Returns:** The complete planning controls data structure with ALL the real planning instruments!

## Complete Planning Controls Data Structure

This endpoint returns **11 planning layers** including:

### SEPPs (State Environmental Planning Policies)
- **SEPP (Sustainable Buildings) 2022** - Climate Zones for BASIX Buildings Map
- **SEPP (Sustainable Buildings) 2022** - Climate Zones for BASIX Alterations Map  
- **SEPP (Sustainable Buildings) 2022** - Water Use Map
- **SEPP (Transport and Infrastructure) 2021** - Thermal Energy from Waste Prohibition

### LEP Controls (Local Environmental Plan)
- **Inner West Local Environmental Plan 2022**
  - Land Zoning Map: R1 General Residential
  - Floor Space Ratio Map: 0.5:1 + Area 5 controls
  - Key Sites Map: Area 1 (Clauses 4.3C, 4.4, 6.14, 6.15)
  - Lot Size Map: 200 m²
  - Acid Sulfate Soils Map: Class 5

### Environmental Data
- Greater Sydney Tree Canopy Cover (2019 & 2022)
- Regional Plan Boundary: Greater Sydney
- Local Aboriginal Land Council: METROPOLITAN

## Critical Issues

1. **Backend IS getting this data** - visible in API server logs
2. **Frontend is NOT receiving it** - basic property intelligence endpoint strips it out
3. **Need to modify backend** to include `planning_controls` in the response
4. **This exact data structure** should be returned to display real planning instrument names

## Solution Required

The backend needs to return the `planning_controls` array from the layer intersect API call in the basic property intelligence response, so the frontend can display:
- Actual SEPP names (not generic counts)
- Real legislative clauses
- Specific map references
- Environmental constraints
- Aboriginal land council info