# Environmental Planning Layers - API Research & Integration Plan

## Executive Summary

| Layer | API Status | Integration Difficulty | Priority |
|-------|-----------|----------------------|----------|
| **Contaminated Land** | No API - download only | High (ETL pipeline needed) | High |
| **Coastal Erosion** | API exists but **NO DATA** | Blocked | Low |
| **Biodiversity Values** | REST API available | Low | Medium |
| **Landslide Risk** | REST API available | Low | Medium |
| **Aircraft Noise (ANEF)** | Subscription required | Medium | Low |

---

## Current Architecture

### API Call Pattern (Already Parallel)

From `nsw-planning-portal.ts` line ~800:
```typescript
const [layers, propertyData, todLayers, roadClassifications] = await Promise.all([
  this.getPlanningLayers(searchResult.propId),
  this.getPropertyValuation(searchResult.propId),
  this.getTODLayers(pd.geometry),
  getRoadClassifications(lat, lon)
]);
```

**New layers would follow this pattern** - added to `Promise.all()` block.

---

## 1. Contaminated Land Register (NSW EPA)

### Current State in PlotDetect
**Partially integrated:**
- SEPP Resilience & Hazards Section 4.6 requirements in `sepp_structured_requirements` table
- Zone-based triggering for industrial zones (IN1, IN2, E4, E5, B5, B6, B7)
- Display component exists: `StructuredSeppRequirements.tsx`

**NOT integrated:**
- Real-time EPA Investigation Areas lookup
- Property-specific contamination status

### Why No API Exists
- EPA provides **monthly Excel/PDF downloads only**
- Web search interface (not programmatic): https://app.epa.nsw.gov.au/prclmapp/searchregister.aspx
- No REST/WFS/WMS service

### Data Sources
| Source | URL | Format |
|--------|-----|--------|
| List of Notified Sites | https://www.epa.nsw.gov.au/your-environment/contaminated-land/notified-and-regulated-contaminated-land/list-of-notified-sites | Excel/PDF monthly |
| Record of Notices | SEED Portal | Download only |
| Investigation Areas | Contact data.broker@environment.nsw.gov.au | Shapefile request |

### Integration Options

**Option A: ETL Pipeline (Recommended)**
1. Monthly scheduled job downloads EPA Excel
2. Geocode addresses to lat/lon
3. Store in Supabase `contaminated_sites` table
4. Query by proximity in `Promise.all()` block

**Option B: Static Import**
1. One-time download of all 2,260 notices (435 sites)
2. Manual geocoding
3. Periodic manual refresh

**Effort Estimate:** 2-3 days for ETL pipeline

---

## 2. Coastal Erosion Hazard

### API Endpoints
```
REST: https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/SEPP_Resilience_and_Hazards_2021/MapServer
WFS: https://mapprod3.environment.nsw.gov.au/arcgis/services/Planning/SEPP_Resilience_and_Hazards_2021/MapServer/WFSServer
```

### CRITICAL ISSUE: No Data Available

**The Coastal Vulnerability Area (CVA) layer has NO spatial data statewide.**

- Councils must submit planning proposals to include their coastal hazard mapping
- As of April 2025, only Coffs Harbour (partial) has completed this
- This is a known gap in the NSW planning system

### Available Layers (that DO have data)
- Coastal Wetlands and Littoral Rainforests Area Map
- Coastal Wetlands
- Littoral Rainforest
- Coastal Environment Area Map
- Coastal Use Area Map

### Recommendation
- **Do not prioritise** until CVA layer is populated
- Could integrate wetlands/littoral rainforest layers as partial coverage
- Consider linking to council-specific coastal studies (not standardised)

---

## 3. Biodiversity Values Map

### API Endpoint (Open Access)
```
REST: https://www.lmbc.nsw.gov.au/arcgis/rest/services/BV/BiodiversityValues/MapServer
```

### Query Pattern
```typescript
const bvMapUrl = 'https://www.lmbc.nsw.gov.au/arcgis/rest/services/BV/BiodiversityValues/MapServer/0/query';
const params = new URLSearchParams({
  geometry: JSON.stringify({ x: lon, y: lat, spatialReference: { wkid: 4326 } }),
  geometryType: 'esriGeometryPoint',
  spatialRel: 'esriSpatialRelIntersects',
  outFields: '*',
  returnGeometry: false,
  f: 'json'
});
```

### Integration
- Add to `Promise.all()` block in `nsw-planning-portal.ts`
- Returns whether property intersects Biodiversity Values Map
- Triggers SEPP Biodiversity Conservation 2021 requirements

### BioNet Species Data (Optional Enhancement)
```
OData API: https://data.bionet.nsw.gov.au/biosvcapp/odata
```
- Requires API token authentication
- 7+ million species sightings
- Could show "X threatened species recorded within 500m"

**Effort Estimate:** 1 day for BV Map, 2-3 days for BioNet

---

## 4. Landslide Risk Map

### API Endpoint (Open Access)
```
REST: https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Hazard/MapServer
Layers: https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Hazard/MapServer/layers
```

### Coverage Limitation
- Only areas where councils have LEP Part 6 landslide provisions
- Not statewide comprehensive coverage
- Inner West: Check if mapped

### Query Pattern
```typescript
const hazardUrl = 'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Hazard/MapServer/0/query';
// Same pattern as BV Map
```

### Integration
- Add to `Promise.all()` block
- Returns landslide risk category if mapped
- Triggers LEP Part 6 local provisions

**Effort Estimate:** 1 day

---

## 5. Aircraft Noise Contours (ANEF)

### Data Source
- Airservices Australia: https://data.airservicesaustralia.com/
- Individual airport ANEFs

### Access Requirements
- **PDF maps:** Free (can digitise manually)
- **Shapefiles:** Subscription required via data.airservicesaustralia.com
- Contact: NoiseEnviroTeam@AirservicesAustralia.com

### Key ANEFs for Inner West
- Sydney Airport ANEF 2039
- Affects properties under flight paths in Marrickville, Tempe, etc.

### Integration Options

**Option A: Subscribe to Airservices**
- Ongoing cost
- Official shapefiles
- Automatic updates

**Option B: Digitise PDF Maps**
- One-time effort
- Sydney Airport ANEF 2039 PDF available free
- Manual updates when ANEF revised (every 5-10 years)

**Option C: Use council 149 certificate data**
- Some councils include ANEF in planning certificates
- Not standardised

**Effort Estimate:** 2-3 days (Option B)

---

## Recommended Integration Order

### Phase 1: Easy Wins (1-2 days)
1. **Biodiversity Values Map** - Open REST API, straightforward
2. **Landslide Risk** - Open REST API, same pattern

### Phase 2: ETL Required (3-5 days)
3. **Contaminated Land** - Build monthly ETL from EPA Excel

### Phase 3: Manual/Subscription (2-3 days)
4. **ANEF** - Digitise Sydney Airport ANEF or subscribe

### Phase 4: Blocked
5. **Coastal Erosion** - Wait for NSW to populate CVA layer

---

## Implementation Pattern

### Add to `nsw-planning-portal.ts`

```typescript
// New function
async getEnvironmentalLayers(geometry: Geometry): Promise<EnvironmentalConstraints> {
  const [biodiversity, landslide, contaminated] = await Promise.all([
    this.queryBiodiversityValuesMap(geometry),
    this.queryLandslideRisk(geometry),
    this.queryContaminatedLand(geometry) // From local Supabase table
  ]);

  return { biodiversity, landslide, contaminated };
}

// Add to main data fetch
const [layers, propertyData, todLayers, roadClassifications, envLayers] = await Promise.all([
  this.getPlanningLayers(searchResult.propId),
  this.getPropertyValuation(searchResult.propId),
  this.getTODLayers(pd.geometry),
  getRoadClassifications(lat, lon),
  this.getEnvironmentalLayers(pd.geometry)  // NEW
]);
```

### New Supabase Table for Contaminated Land

```sql
CREATE TABLE contaminated_sites (
  id SERIAL PRIMARY KEY,
  site_name TEXT,
  address TEXT,
  suburb TEXT,
  lat DECIMAL(10, 7),
  lon DECIMAL(10, 7),
  notice_type TEXT,  -- 'investigation', 'remediation', 'audit'
  epa_reference TEXT,
  status TEXT,
  last_updated DATE,
  geometry GEOMETRY(Point, 4326)
);

CREATE INDEX idx_contaminated_sites_geometry ON contaminated_sites USING GIST(geometry);
```

---

## Key Risks

1. **Contaminated Land geocoding accuracy** - EPA addresses may not geocode cleanly
2. **Landslide coverage gaps** - Many councils haven't mapped
3. **Coastal erosion data gap** - Statewide issue, not our problem to solve
4. **ANEF subscription cost** - Unknown, may be significant

---

## Questions Before Implementation

1. Is Inner West Council area mapped for landslide risk?
2. What's the Airservices subscription cost for ANEF shapefiles?
3. Should we show "no data available" for layers with coverage gaps?
4. Priority: Which layer provides most user value for Inner West properties?
