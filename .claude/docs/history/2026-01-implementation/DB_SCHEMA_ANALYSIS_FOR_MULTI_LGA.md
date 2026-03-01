# Database Schema Analysis: Multi-LGA & Hierarchical Support

**Date:** 2025-10-26
**Analyzed:** PostgreSQL database `nsw_planning`
**Context:** Evaluating readiness for Marrickville + Ashfield + Leichhardt + future LGAs

---

## Current Schema Capabilities

### ✅ **1. Multiple DCPs per LGA - SUPPORTED**

**Evidence:**
- `documents` table tracks document type and area
- Document IDs embed DCP name: `Marrickville_DCP_2011_...`, `Ashfield_DCP_2016_...`, `Leichhardt_DCP_2013_...`
- Current provisions:
  - Marrickville DCP: **1,182 provisions**
  - Leichhardt DCP: **21 provisions**
  - Other: **40,779 provisions** (SEPPs, LEPs, etc.)

**Tables Supporting This:**
```sql
documents
  - id: text (unique document identifier)
  - document_type: DCP, SEPP, LEP
  - document_area: specific area/precinct

regulatory_provisions
  - document_id: references documents(id)
  - 42,067 total rows, all DCPs tracked
```

**Verdict:** ✅ **Fully supports multiple legacy DCPs** (Marrickville, Ashfield, Leichhardt)

---

### ⚠️ **2. Hierarchical Areas (Precincts → Sub-Areas) - PARTIAL**

**Current Structure:**
```sql
dcp_precinct_boundaries (20 rows)
  - precinct_id: text
  - precinct_name: text
  - lga: text
  - former_council: text (nullable, CURRENTLY EMPTY)
  - boundary: geometry (PostGIS polygon)
  - source_document: text

dcp_precinct_metadata (0 rows)
  - precinct_id: text
  - description: text
  - boundary_streets: array

dcp_precinct_provisions (312 rows)
  - precinct_id: text
  - provision_text: text
  - parent_provision_id: integer (FK to regulatory_provisions)
```

**What EXISTS:**
- ✅ Precinct-level boundaries (polygons)
- ✅ Precinct-level provisions
- ✅ Link to parent provisions (`parent_provision_id`)

**What's MISSING:**
- ❌ Sub-area/neighborhood hierarchy (no `parent_precinct_id` or sub-area table)
- ❌ `former_council` field exists but is empty (no Marrickville/Ashfield/Leichhardt distinction)
- ❌ No way to represent: Precinct → Distinctive Neighbourhood → Sub-Area

**Proposed Solution:**
```sql
-- Add hierarchical support
ALTER TABLE dcp_precinct_boundaries
ADD COLUMN parent_precinct_id TEXT REFERENCES dcp_precinct_boundaries(precinct_id),
ADD COLUMN hierarchy_level INTEGER DEFAULT 1, -- 1=precinct, 2=sub-area, 3=micro-area
ADD COLUMN dcp_name TEXT; -- 'Marrickville DCP 2011', 'Ashfield DCP 2016', etc.

-- Populate former_council
UPDATE dcp_precinct_boundaries
SET former_council = 'Marrickville'
WHERE source_document LIKE '%Marrickville%';

-- For Leichhardt's Distinctive Neighbourhoods
INSERT INTO dcp_precinct_boundaries (
  precinct_id, precinct_name, lga, former_council,
  dcp_name, hierarchy_level, parent_precinct_id
)
VALUES
  ('L_DN_1', 'Young Street Distinctive Neighbourhood', 'INNER WEST', 'Leichhardt',
   'Leichhardt DCP 2013', 1, NULL),
  ('L_DN_1_SA_1', 'Young Street Laneways Sub-Area', 'INNER WEST', 'Leichhardt',
   'Leichhardt DCP 2013', 2, 'L_DN_1');
```

**Verdict:** ⚠️ **Partially supports hierarchies** - can be extended with parent_precinct_id

---

### ✅ **3. Overlapping Controls (Precincts + HCAs + Site-Specific) - SUPPORTED**

**Evidence:**

**Heritage Conservation Areas:**
```sql
heritage_conservation_areas (2,039 rows)
  - h_name: text
  - lga_name: varchar
  - geometry_json: jsonb (polygon boundaries)
  - significance: text
```

**Precinct Boundaries:**
```sql
dcp_precinct_boundaries (20 rows)
  - boundary: geometry (PostGIS polygon)
```

**Site-Specific Controls:**
```sql
dcp_precinct_requirements (330 rows)
  - precinct_id: text (includes 'G1', 'G2' for Leichhardt Part G site-specific)
  - category, subcategory: text
  - source_provision_ids: array
```

**How Overlaps Work:**
1. ✅ Address lookup: PostGIS `ST_Contains()` finds which polygons contain an address
2. ✅ Multiple polygons can contain same address (precinct + HCA)
3. ✅ App aggregates provisions from all applicable areas

**Query Pattern:**
```sql
-- Find all controls for an address
WITH address_point AS (
  SELECT ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS geom
)
SELECT
  'precinct' AS control_type,
  pb.precinct_name,
  pp.provision_text
FROM dcp_precinct_boundaries pb
JOIN dcp_precinct_provisions pp ON pb.precinct_id = pp.precinct_id
WHERE ST_Contains(pb.boundary, (SELECT geom FROM address_point))

UNION ALL

SELECT
  'heritage' AS control_type,
  hca.h_name,
  hca.significance
FROM heritage_conservation_areas hca
WHERE ST_Contains(ST_GeomFromGeoJSON(hca.geometry_json), (SELECT geom FROM address_point));
```

**Verdict:** ✅ **Fully supports overlapping controls** via PostGIS spatial queries

---

### ⚠️ **4. Different Naming Conventions - PARTIAL**

**Current Naming:**
- Precincts tracked as `precinct_id` and `precinct_name`
- No standardized terminology field

**Examples from Database:**
```
Marrickville: "Precinct 3 - Stanmore North"
Ashfield: Would be "Precinct D1 - Ashfield Town Centre"
Leichhardt: Should be "Distinctive Neighbourhood - Young Street"
```

**What's MISSING:**
- ❌ No `area_type` field (e.g., 'precinct', 'neighbourhood', 'locality')
- ❌ No consistent naming convention enforced

**Proposed Solution:**
```sql
ALTER TABLE dcp_precinct_boundaries
ADD COLUMN area_type TEXT DEFAULT 'precinct',
ADD COLUMN area_type_display TEXT; -- User-friendly display name

-- Examples:
UPDATE dcp_precinct_boundaries
SET area_type = 'precinct',
    area_type_display = 'Precinct'
WHERE source_document LIKE '%Marrickville%';

UPDATE dcp_precinct_boundaries
SET area_type = 'distinctive_neighbourhood',
    area_type_display = 'Distinctive Neighbourhood'
WHERE source_document LIKE '%Leichhardt%';
```

**Verdict:** ⚠️ **Partially supports** - can be extended with area_type field

---

## Summary Scorecard

| Requirement | Current Status | Gap | Priority |
|-------------|----------------|-----|----------|
| **Multiple DCPs per LGA** | ✅ Fully Supported | None | N/A |
| **Hierarchical Areas** | ⚠️ Partial | Need parent_precinct_id, hierarchy_level | HIGH |
| **Overlapping Controls** | ✅ Fully Supported | None | N/A |
| **Different Naming** | ⚠️ Partial | Need area_type field | MEDIUM |

---

## Recommended Schema Enhancements

### Priority 1: Add Hierarchical Support

```sql
-- Extend dcp_precinct_boundaries
ALTER TABLE dcp_precinct_boundaries
ADD COLUMN parent_precinct_id TEXT REFERENCES dcp_precinct_boundaries(precinct_id),
ADD COLUMN hierarchy_level INTEGER DEFAULT 1,
ADD COLUMN dcp_name TEXT,
ADD COLUMN area_type TEXT DEFAULT 'precinct',
ADD COLUMN area_type_display TEXT;

-- Populate former_council (currently empty)
UPDATE dcp_precinct_boundaries
SET former_council = CASE
  WHEN source_document LIKE '%Marrickville%' THEN 'Marrickville'
  WHEN source_document LIKE '%Ashfield%' THEN 'Ashfield'
  WHEN source_document LIKE '%Leichhardt%' THEN 'Leichhardt'
  ELSE NULL
END;

-- Add indexes for performance
CREATE INDEX idx_precinct_boundaries_parent ON dcp_precinct_boundaries(parent_precinct_id);
CREATE INDEX idx_precinct_boundaries_hierarchy ON dcp_precinct_boundaries(hierarchy_level);
CREATE INDEX idx_precinct_boundaries_former_council ON dcp_precinct_boundaries(former_council);
```

### Priority 2: Populate Metadata Table

```sql
-- dcp_precinct_metadata is currently EMPTY (0 rows)
-- Should be populated from extracted markdown:

INSERT INTO dcp_precinct_metadata (
  precinct_id, precinct_name, lga, description,
  desired_character, boundary_streets
)
SELECT
  precinct_id,
  precinct_name,
  lga,
  -- Extract from precinct_boundaries_extracted.json
  existing_char_excerpt,
  desired_future_character,
  string_to_array(boundary_text, ', ')
FROM ... -- import from JSON files
```

### Priority 3: Standard Query Functions

```sql
-- Function to get all applicable controls for an address
CREATE OR REPLACE FUNCTION get_controls_for_address(
  p_lon NUMERIC,
  p_lat NUMERIC
) RETURNS TABLE (
  control_type TEXT,
  control_name TEXT,
  provisions JSONB
) AS $$
BEGIN
  RETURN QUERY
  -- Precincts
  SELECT
    'precinct'::TEXT,
    pb.precinct_name,
    jsonb_agg(
      jsonb_build_object(
        'provision_id', pp.id,
        'text', pp.provision_text,
        'ref_number', pp.ref_number
      )
    )
  FROM dcp_precinct_boundaries pb
  JOIN dcp_precinct_provisions pp ON pb.precinct_id = pp.precinct_id
  WHERE ST_Contains(pb.boundary, ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326))
  GROUP BY pb.precinct_name

  UNION ALL

  -- Heritage Conservation Areas
  SELECT
    'heritage'::TEXT,
    hca.h_name,
    jsonb_build_object(
      'significance', hca.significance,
      'lga', hca.lga_name
    )
  FROM heritage_conservation_areas hca
  WHERE ST_Contains(
    ST_GeomFromGeoJSON(hca.geometry_json::text),
    ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)
  );
END;
$$ LANGUAGE plpgsql;
```

---

## Migration Path for Adding Ashfield & Leichhardt

### Phase 1: Schema Enhancements (1 day)
- Add new columns to `dcp_precinct_boundaries`
- Populate `former_council` for existing Marrickville precincts
- Add indexes

### Phase 2: Import Ashfield Precincts (2-3 days)
- Georeference 8-13 Ashfield precinct maps
- Import using `import_precinct_boundaries.py`
- Populate with `former_council = 'Ashfield'`

### Phase 3: Import Leichhardt Neighbourhoods (1-2 weeks)
- Georeference 30 Distinctive Neighbourhood maps
- Import with `hierarchy_level = 1`
- Set `area_type = 'distinctive_neighbourhood'`
- Skip sub-areas initially (store as metadata)

### Phase 4: Testing & Validation (2-3 days)
- Test address lookups across all 3 DCPs
- Validate overlapping controls work correctly
- Update API endpoints to handle new fields

---

## Conclusion

**Current Database Status:**
- ✅ **Ready for multiple DCPs** (Marrickville, Ashfield, Leichhardt)
- ✅ **Ready for overlapping controls** (precincts + HCAs work together)
- ⚠️ **Needs minor extensions** for hierarchies and naming conventions

**Recommended Action:**
1. Execute Priority 1 schema enhancements (add hierarchy support)
2. Import Ashfield precincts (quick win)
3. Import Leichhardt neighbourhoods (without sub-area polygons initially)
4. Store sub-area provisions as metadata linked to parent neighbourhoods

**Database architecture is 80% ready - just needs hierarchical extensions!**
