# Complete Precinct Integration Workflow
**From Georeferencing to Working Address-Based Filtering**

## Current State vs Goal

### Current State
- ✅ `dcp_precinct_provisions` table EXISTS with 45 precincts (provisions text)
- ❌ `dcp_precinct_boundaries` table DOES NOT EXIST (no geometry)
- ❌ Precinct matching uses HARDCODED street names (broken for many addresses)
- ❌ Example: "20 Pile St, Dulwich Hill" shows NO precinct provisions (even though they exist in database)

### Goal
- ✅ When user enters an address, app automatically determines which precinct it's in
- ✅ Only shows DCP provisions relevant to that precinct
- ✅ Works for ALL addresses in Inner West (not just hardcoded streets)

## The Missing Piece: Precinct Boundaries

**From**: `PRECINCT_MATCHING_PROPER_SOLUTION.md`

The app needs to do a **geometric point-in-polygon query**:
1. Get property coordinates from NSW Planning Portal API
2. Query: "Which precinct polygon contains this point?"
3. Return provisions for that precinct

**This requires**:
- PostGIS extension (for spatial queries)
- `dcp_precinct_boundaries` table with polygon geometry
- Precinct boundary data (from georeferencing!)

## Complete Workflow

### Phase 1: Setup PostGIS (5 minutes)

**Check if PostGIS is installed**:
```sql
SELECT PostGIS_Version();
```

**If not installed**, follow: `POSTGIS_SETUP_COMPLETE_GUIDE.md`

Or run:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

### Phase 2: Create Boundaries Table (2 minutes)

**Run this SQL**:
```sql
CREATE TABLE IF NOT EXISTS dcp_precinct_boundaries (
  id SERIAL PRIMARY KEY,
  precinct_id TEXT NOT NULL,
  precinct_name TEXT NOT NULL,
  lga TEXT NOT NULL DEFAULT 'INNER WEST',
  former_council TEXT,  -- Marrickville, Ashfield, Leichhardt
  boundary GEOMETRY(POLYGON, 4326),  -- WGS84 lat/lon coordinates
  source_document TEXT,  -- Which PDF the boundary came from
  extraction_method TEXT DEFAULT 'manual',  -- manual, digitized, api
  confidence_score FLOAT DEFAULT 0.95,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT unique_precinct_lga UNIQUE (precinct_id, lga)
);

-- Create spatial index for fast point-in-polygon queries
CREATE INDEX idx_precinct_boundaries_geom
  ON dcp_precinct_boundaries USING GIST(boundary);

CREATE INDEX idx_precinct_boundaries_lga
  ON dcp_precinct_boundaries(lga);

-- Allow user postgres to insert/update
GRANT ALL ON dcp_precinct_boundaries TO postgres;
GRANT USAGE, SELECT ON SEQUENCE dcp_precinct_boundaries_id_seq TO postgres;
```

### Phase 3: Georeference Maps (60 minutes for all 20)

**Follow**: `SIMPLE_GEOREFERENCING_WITH_OSM.md`

**Quick summary**:
1. ✅ OSM layer already loaded in QGIS
2. Open QGIS Georeferencer
3. Load precinct PDF (e.g., `output/Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3/auto/*_span.pdf`)
4. Add 4 control points using "From Map Canvas" button
5. Run georeferencing → Saves to `output/precinct_X_georeferenced.tif`

**Output**: 20 georeferenced TIF files with correct coordinates

### Phase 4: Digitize Boundaries (90 minutes for all 20)

**This is the KEY step** that saves boundaries to the database!

#### 4.1. Create New Vector Layer in QGIS

1. In QGIS: Layer → Create Layer → New GeoPackage Layer
2. Database: `precinct_boundaries.gpkg`
3. Table name: `boundaries`
4. Geometry type: **Polygon**
5. CRS: **EPSG:4326 - WGS84**
6. Add fields:
   - `precinct_id` (Text, length 10)
   - `precinct_name` (Text, length 100)
   - `lga` (Text, length 50)
7. Click OK

#### 4.2. Digitize Each Precinct Boundary

For each georeferenced precinct map:

1. **Load georeferenced raster**:
   - Layer → Add Layer → Add Raster Layer
   - Select: `output/precinct_3__georeferenced.tif`

2. **Enable editing** on the boundaries layer:
   - Click the boundaries layer
   - Click the pencil icon (Toggle Editing)

3. **Add polygon**:
   - Click "Add Polygon Feature" button
   - Click along the precinct boundary shown on the map
   - Right-click to finish
   - Enter attributes:
     - precinct_id: `3_`
     - precinct_name: `Stanmore North Precinct 3`
     - lga: `INNER WEST`

4. **Save edits**:
   - Click "Save Layer Edits" button

5. **Repeat** for remaining 19 precincts

#### 4.3. Export to PostGIS Database

**Option A: Direct Export to PostGIS (Recommended)**

1. Right-click the boundaries layer → Export → Save Features As
2. Format: **PostgreSQL**
3. Connection:
   - Host: `localhost`
   - Port: `5432`
   - Database: `nsw_planning`
   - User: `postgres`
   - Password: [your password]
4. Schema: `public`
5. Table: `dcp_precinct_boundaries`
6. Click OK

**Option B: Export to GeoJSON then Import**

1. Right-click boundaries layer → Export → Save Features As
2. Format: **GeoJSON**
3. File: `precinct_boundaries.geojson`
4. CRS: **EPSG:4326**
5. Click OK

Then import to PostGIS:
```python
import json
import psycopg2
from shapely.geometry import shape

# Load GeoJSON
with open('precinct_boundaries.geojson') as f:
    geojson = json.load(f)

# Connect to database
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='your_password'
)
cur = conn.cursor()

# Insert each feature
for feature in geojson['features']:
    props = feature['properties']
    geom = shape(feature['geometry'])

    cur.execute('''
        INSERT INTO dcp_precinct_boundaries
        (precinct_id, precinct_name, lga, boundary,
         extraction_method, confidence_score, source_document)
        VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326),
                'manual', 0.95, %s)
        ON CONFLICT (precinct_id, lga)
        DO UPDATE SET
            boundary = EXCLUDED.boundary,
            updated_at = NOW()
    ''', (
        props['precinct_id'],
        props['precinct_name'],
        props['lga'],
        geom.wkt,
        f"Marrickville DCP 2011 - 9 {props['precinct_id']}"
    ))

conn.commit()
print(f"Imported {len(geojson['features'])} precinct boundaries")
```

### Phase 5: Verify Database (2 minutes)

```sql
-- Check boundaries were imported
SELECT
    precinct_id,
    precinct_name,
    ST_Area(boundary) as area,
    ST_AsText(ST_Centroid(boundary)) as center
FROM dcp_precinct_boundaries
ORDER BY precinct_id;

-- Should show 20 rows with polygon geometry
```

**Test a point-in-polygon query**:
```sql
-- Test: Is 20 Pile St in a precinct?
-- Pile St, Dulwich Hill coordinates: approximately (151.1385, -33.9052)

SELECT
    precinct_id,
    precinct_name
FROM dcp_precinct_boundaries
WHERE ST_Contains(
    boundary,
    ST_SetSRID(ST_MakePoint(151.1385, -33.9052), 4326)
);

-- Expected: Precinct 10_ (Dulwich Hill North)
```

### Phase 6: Update Precinct Service Code (30 minutes)

**File**: `frontend-nextjs/lib/precinct-service.ts`

Replace the hardcoded street matching with geometric matching:

```typescript
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'nsw_planning',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD
});

/**
 * Get precinct for an address using geometric matching
 */
export async function getPrecinctForAddress(
  address: string,
  lga: string
): Promise<PrecinctMapping | null> {
  try {
    console.log('[Precinct Service] Looking up precinct for:', { address, lga });

    // Step 1: Get property coordinates from NSW Planning Portal
    const propertyData = await fetch('/api/property', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address })
    }).then(res => res.json());

    if (!propertyData?.property?.geometry?.x) {
      console.log('[Precinct Service] No coordinates found');
      return null;
    }

    const { x, y } = propertyData.property.geometry;
    console.log('[Precinct Service] Property coordinates:', { x, y });

    // Step 2: Query precinct boundaries using point-in-polygon
    // NSW Planning Portal returns MGA94 Zone 56 coordinates
    const query = `
      SELECT
        precinct_id,
        precinct_name,
        lga,
        confidence_score
      FROM dcp_precinct_boundaries
      WHERE ST_Contains(
        boundary,
        ST_Transform(
          ST_SetSRID(ST_MakePoint($1, $2), 7856),  -- MGA94 Zone 56
          4326  -- Convert to WGS84
        )
      )
      AND LOWER(lga) = LOWER($3)
      ORDER BY confidence_score DESC
      LIMIT 1
    `;

    const result = await pool.query(query, [x, y, lga]);

    if (result.rows.length === 0) {
      console.log('[Precinct Service] No precinct contains this point');
      return null;
    }

    const precinct = result.rows[0];
    console.log('[Precinct Service] Matched to precinct:', precinct.precinct_id);

    return {
      precinctNumber: precinct.precinct_id,
      precinctName: precinct.precinct_name,
      documentId: buildPrecinctDocumentId(precinct.precinct_id, precinct.precinct_name),
      lga: precinct.lga,
      confidenceScore: precinct.confidence_score
    };

  } catch (error) {
    console.error('[Precinct Service] Error:', error);
    return null;
  }
}

function buildPrecinctDocumentId(precinctId: string, precinctName: string): string {
  const nameSlug = precinctName.replace(/ /g, '_');
  return `Marrickville_DCP_2011_${precinctId}_${nameSlug}`;
}
```

### Phase 7: Test Complete Workflow (5 minutes)

**Test Address**: `20 Pile Street, Dulwich Hill NSW 2203`

**Expected Flow**:
1. User enters address in app
2. NSW Planning Portal API returns coordinates: (151.1385, -33.9052)
3. PostGIS query finds Precinct 10_ (Dulwich Hill North)
4. App fetches provisions from `dcp_precinct_provisions` WHERE precinct_id = '10_'
5. Displays 4 precinct-specific provisions

**Verify**:
```bash
# Start dev server
cd frontend-nextjs
npm run dev

# Test in browser
http://localhost:3000/assessment

# Enter:
# - Address: 20 Pile Street, Dulwich Hill NSW 2203
# - Zone: R2
# - Development Type: Dwelling House

# Expected:
# - Precinct section appears
# - Shows "Precinct 10: Dulwich Hill North"
# - Lists 4 provisions
```

## Time Breakdown

| Phase | Task | Time |
|-------|------|------|
| 1 | Install PostGIS | 5 min |
| 2 | Create boundaries table | 2 min |
| 3 | Georeference 20 maps | 60 min |
| 4 | Digitize 20 boundaries | 90 min |
| 5 | Export to PostGIS | 5 min |
| 6 | Update code | 30 min |
| 7 | Test | 5 min |
| **TOTAL** | | **~3 hours** |

## What Each Part Does

| Component | Purpose | Status |
|-----------|---------|--------|
| **Georeferenced TIFs** | Visual reference for digitizing | From Phase 3 |
| **Precinct boundaries (polygons)** | Stored in `dcp_precinct_boundaries` | From Phase 4 |
| **Precinct provisions (text)** | Stored in `dcp_precinct_provisions` | ✅ Already exists |
| **Geometric matching code** | Finds precinct for address | From Phase 6 |

## Troubleshooting

### "PostGIS function not found"
**Fix**: Install PostGIS extension (see Phase 1)

### "Coordinates in wrong location"
**Fix**: Check if NSW Planning Portal uses MGA94 or WGS84. Adjust `ST_Transform` SRID accordingly.

### "No precinct found for address"
**Fix**:
1. Check if boundary polygon covers that location in QGIS
2. Verify coordinates are in correct CRS
3. Test with ST_Distance to find nearest precinct

### "Multiple precincts found"
**Fix**: Boundaries overlap. Refine polygon edges in QGIS.

## Summary

**Before** (Current State):
- Hardcoded street names
- Only works for ~30 precincts
- Broken for Dulwich Hill (2203 postcode)

**After** (This Workflow):
- Geometric point-in-polygon matching
- Works for ALL addresses in database
- Accurate, maintainable, scalable

**Next Steps**:
1. Follow `SIMPLE_GEOREFERENCING_WITH_OSM.md` to georeference maps
2. Digitize boundaries in QGIS (Phase 4)
3. Export to PostGIS (Phase 5)
4. Update code (Phase 6)
5. Test with real addresses (Phase 7)

**Key Files**:
- Setup: `POSTGIS_SETUP_COMPLETE_GUIDE.md`
- Georeferencing: `SIMPLE_GEOREFERENCING_WITH_OSM.md`
- Architecture: `PRECINCT_MATCHING_PROPER_SOLUTION.md`
- Implementation: `PRECINCT_IMPLEMENTATION_CHECKLIST.md`
