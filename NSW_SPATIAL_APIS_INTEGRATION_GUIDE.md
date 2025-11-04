# NSW Spatial APIs Integration Guide
## Free APIs for Road/Reserve Boundaries & Setback Calculations

### Executive Summary
This document maps free NSW government APIs for obtaining road boundaries, reserve boundaries, and cadastral data needed for automated setback calculations in the planning compliance engine.

---

## 🎯 Required Data for Setback Calculations

Based on DCP requirements, we need:
1. **Primary road boundary** - 4.5m, 6.5m, or 10m setback (based on lot area)
2. **Public reserve boundary** - Minimum 3m setback
3. **Secondary road boundary** - Variable setback
4. **Lot boundaries** - For lot area calculation
5. **Road classification** - To determine if primary/secondary

---

## 📡 Available Free APIs

### 1. NSW Cadastre Web Service (Lot Boundaries)
**Provider:** NSW Spatial Services
**License:** Creative Commons Attribution (Free)
**Format:** OGC-compliant WMS/WFS

#### Service URLs:
```
Map Server (WMS): https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer
API Access: https://data.nsw.gov.au/api/3/action/package_show?id=b8659c69-7666-4b5d-97a9-3c5036f50315
```

#### Feature Layers:
- **Lot Boundaries** - Cadastral lot polygons
- **Section Extents** - Section boundaries
- **Plan Extents** - Plan boundaries

#### Queryable Attributes:
- `cadid` - Cadastral ID
- `lot_number`
- `section_number`
- `plan_number`
- `lot_area` - ✅ **Critical for setback calculation**

#### Use Case:
Query lot boundaries by coordinates to get:
- Exact lot polygon
- Lot area (determines 4.5m vs 6.5m vs 10m front setback for Ashfield)
- Adjacent lot identifiers

#### Example Query:
```javascript
// WFS GetFeature request
const lotQuery = `
https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/0/query
?geometry=${longitude},${latitude}
&geometryType=esriGeometryPoint
&spatialRel=esriSpatialRelIntersects
&outFields=*
&returnGeometry=true
&f=json
`;
```

---

### 2. NSW Road Segment Dataset (Road Classifications)
**Provider:** Transport for NSW
**License:** Free/Open Data
**Format:** GeoJSON, Shapefile, API

#### Service URLs:
```
Data Portal: https://data.nsw.gov.au/data/dataset/?tags=roads
TfNSW Open Data Hub: https://opendata.transport.nsw.gov.au/dataset/road-segment-data-from-datansw
FSDF Link: https://link.fsdf.org.au/dataset/nsw-road-segment-dataset
```

#### Road Classifications:
- Motorways
- Primary roads ✅ **(determines primary road setback)**
- Arterial roads
- Sub-arterial roads
- Distributor roads
- Local roads ✅ **(determines secondary road setback)**
- Urban service road
- Track-vehicular

#### Attributes:
- `road_name`
- `road_type` - Classification (primary/local/etc)
- `road_surface`
- `lane_count`
- `road_hierarchy` - ✅ **Critical for setback rules**

#### Use Case:
Query roads adjacent to lot to determine:
- Is it a primary road? (4.5m/6.5m/10m setback)
- Is it a secondary road? (variable setback)
- Road name for display

---

### 3. NSW National Parks & Wildlife Service Estate (Public Reserves)
**Provider:** NSW Department of Planning & Environment
**License:** Free/Open Data
**Format:** WFS/WMS

#### Service URLs:
```
SEED Portal: https://datasets.seed.nsw.gov.au/dataset/nsw-national-parks-and-wildlife-service-npws-estate3f9e7
Data.NSW: https://data.nsw.gov.au/data/dataset/nsw-national-parks-and-wildlife-service-npws-estate3f9e7
```

#### Reserve Types:
- National Parks
- Nature Reserves
- Regional Parks ✅ **(3m setback requirement)**
- State Conservation Areas
- Aboriginal Areas
- Historic Sites

#### Attributes:
- `reserve_name`
- `reserve_type`
- `gazettal_date`
- `area_ha`
- Boundary geometry

#### Use Case:
Query if lot is adjacent to public reserve:
- Apply 3m minimum setback to reserve boundary
- Display reserve name in compliance report

---

### 4. NSW Planning Portal Spatial Viewer (Integration Point)
**Provider:** NSW Department of Planning & Environment
**URL:** https://www.planningportal.nsw.gov.au/spatialviewer/

#### Capabilities:
- Combines cadastre, zoning, overlays, and environmental data
- Already integrated in our system (we use this for lot lookup)
- Could extend to query road/reserve layers

#### Integration Strategy:
Currently we call:
```javascript
const response = await fetch(
  'https://api.apps1.nsw.gov.au/eplanning/address/v1/properties',
  { params: { address } }
);
```

**Extend to include:**
- Road classification layer
- Reserve boundary layer
- Adjacent lot boundaries

---

## 🔧 Integration Architecture

### Parallel API Call Strategy

```typescript
// frontend-nextjs/lib/spatial-boundary-service.ts

interface SetbackBoundaries {
  lot: {
    geometry: GeoJSON.Polygon;
    area_sqm: number;
    cadid: string;
  };
  roads: Array<{
    name: string;
    classification: 'primary' | 'local' | 'arterial';
    geometry: GeoJSON.LineString;
    distance_from_lot: number;
  }>;
  reserves: Array<{
    name: string;
    type: string;
    geometry: GeoJSON.Polygon;
    distance_from_lot: number;
  }>;
}

async function getSetbackBoundaries(
  lat: number,
  lon: number
): Promise<SetbackBoundaries> {
  // Parallel API calls for optimal performance
  const [lotData, roadData, reserveData] = await Promise.all([
    fetchCadastreData(lat, lon),      // NSW Cadastre API
    fetchRoadData(lat, lon),           // TfNSW Roads API
    fetchReserveData(lat, lon)         // NPWS Reserves API
  ]);

  return {
    lot: processCadastreResponse(lotData),
    roads: processRoadResponse(roadData),
    reserves: processReserveResponse(reserveData)
  };
}
```

### Setback Calculation Logic

```typescript
// frontend-nextjs/lib/setback-calculator.ts

interface SetbackRequirements {
  front: { value: number; reason: string };
  rear: { value: number; reason: string };
  side_primary: { value: number; reason: string };
  side_secondary: { value: number; reason: string };
}

function calculateSetbacks(
  boundaries: SetbackBoundaries,
  zone: string,
  developmentType: string,
  formerCouncil: 'Ashfield' | 'Marrickville' | 'Leichhardt'
): SetbackRequirements {

  // Example: Ashfield front setback logic
  if (formerCouncil === 'Ashfield') {
    const primaryRoad = boundaries.roads.find(r => r.classification === 'primary');

    if (primaryRoad) {
      const lotArea = boundaries.lot.area_sqm;

      if (lotArea < 450) {
        return { front: { value: 4.5, reason: 'Lot area < 450sqm - Ashfield DCP Chapter F' } };
      } else if (lotArea < 600) {
        return { front: { value: 6.5, reason: 'Lot area 450-600sqm - Ashfield DCP Chapter F' } };
      } else {
        return { front: { value: 10, reason: 'Lot area > 600sqm - Ashfield DCP Chapter F' } };
      }
    }
  }

  // Reserve setback
  const adjacentReserve = boundaries.reserves.find(r => r.distance_from_lot < 1);
  if (adjacentReserve) {
    return {
      ...setbacks,
      rear: { value: 3, reason: `Adjacent to ${adjacentReserve.name} - minimum 3m` }
    };
  }

  return setbacks;
}
```

---

## 🚀 Implementation Plan

### Phase 1: Cadastre Integration (Week 1)
- [ ] Create `spatial-boundary-service.ts`
- [ ] Implement NSW Cadastre API client
- [ ] Test lot boundary + area retrieval
- [ ] Cache responses (15min TTL)

### Phase 2: Road Classification (Week 2)
- [ ] Integrate TfNSW Roads API
- [ ] Identify primary vs secondary roads
- [ ] Calculate distance from lot to road centerline
- [ ] Handle corner lots (two road frontages)

### Phase 3: Reserve Boundaries (Week 3)
- [ ] Integrate NPWS Reserves API
- [ ] Detect adjacent reserves
- [ ] Calculate minimum distance to reserve boundary
- [ ] Display reserve names in UI

### Phase 4: Setback Calculator (Week 4)
- [ ] Implement `setback-calculator.ts`
- [ ] Apply Ashfield lot-area-based logic
- [ ] Apply Marrickville/Leichhardt rules
- [ ] Generate human-readable explanations
- [ ] Unit tests for edge cases

### Phase 5: UI Integration (Week 5)
- [ ] Add "View Setback Map" component
- [ ] Display lot boundary, roads, reserves on Mapbox
- [ ] Show calculated setback lines
- [ ] Color code: green (compliant), red (non-compliant)

---

## 📊 Example API Response Formats

### NSW Cadastre Response
```json
{
  "features": [
    {
      "attributes": {
        "cadid": "1234567",
        "lot_number": "10",
        "plan_number": "DP123456",
        "lot_area": 580.5,
        "address": "180 ADDISON ROAD MARRICKVILLE"
      },
      "geometry": {
        "rings": [[[151.15, -33.91], [151.15, -33.91], ...]]
      }
    }
  ]
}
```

### TfNSW Roads Response
```json
{
  "features": [
    {
      "properties": {
        "road_name": "ADDISON ROAD",
        "road_type": "Local",
        "road_hierarchy": "Local Road",
        "surface": "Sealed",
        "lanes": 2
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [[151.15, -33.91], [151.16, -33.91]]
      }
    }
  ]
}
```

### NPWS Reserves Response
```json
{
  "features": [
    {
      "properties": {
        "name": "Enmore Park",
        "type": "Regional Park",
        "gazettal_date": "2015-03-20",
        "area_ha": 4.5
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[151.15, -33.91], ...]]
      }
    }
  ]
}
```

---

## 💰 Cost Analysis

| API Service | Cost | Rate Limits | Notes |
|-------------|------|-------------|-------|
| NSW Cadastre | **Free** | None documented | CC-BY license |
| TfNSW Roads | **Free** | Unknown | Open Data |
| NPWS Reserves | **Free** | None documented | Open Data |
| NSW Planning Portal | **Free** (current) | 60 req/min | Already integrated |

**Total monthly cost: $0** ✅

---

## 🔐 Authentication & Keys

### NSW Cadastre
- **No API key required** for public WMS/WFS
- **No authentication** needed
- **Rate limiting:** Not documented (likely generous)

### TfNSW Roads
- **No API key required** for open datasets
- Available via Data.NSW portal (no auth)

### NPWS Reserves
- **No API key required**
- Available via SEED/Data.NSW (public access)

### NSW Planning Portal
- **API key required** for transactional APIs (DA lodgement, etc)
- **No key required** for spatial viewer queries (what we use)

---

## 📝 Next Steps

1. **Test API endpoints** with real coordinates
2. **Create API client library** (`lib/spatial-boundary-service.ts`)
3. **Implement parallel API calls** (Promise.all pattern)
4. **Add caching layer** (Redis or in-memory with 15min TTL)
5. **Build setback calculator** with DCP rules
6. **Create UI component** for visual setback display
7. **Write integration tests** with sample addresses

---

## 📚 Reference Links

- **NSW Cadastre:** https://data.nsw.gov.au/data/dataset/spatial-services-nsw-cadastre
- **TfNSW Roads:** https://opendata.transport.nsw.gov.au/dataset/road-segment-data-from-datansw
- **NPWS Reserves:** https://datasets.seed.nsw.gov.au/dataset/nsw-national-parks-and-wildlife-service-npws-estate3f9e7
- **NSW Planning Portal:** https://www.planningportal.nsw.gov.au/spatialviewer/
- **Data.NSW:** https://data.nsw.gov.au/
- **SEED Portal:** https://datasets.seed.nsw.gov.au/

---

## ⚠️ Important Notes

### Coordinate System
All APIs use **GDA2020 / MGA Zone 56** (EPSG:7856) or **WGS84** (EPSG:4326). Ensure coordinate transformation if mixing systems.

### Data Currency
- Cadastre: Updated nightly from DCDB
- Roads: Updated quarterly
- Reserves: Updated as gazetted

### Limitations
- **Corner lots:** May have 2+ road frontages (need to identify all)
- **Battle-axe blocks:** Access handle may affect setback calculation
- **Irregular boundaries:** Setback is measured perpendicular, not straight-line distance
- **Rear lanes:** May be classified as "road" but different setback rules apply

---

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Author:** Claude (Compliance Engine Development)
